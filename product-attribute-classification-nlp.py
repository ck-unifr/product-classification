# Farfetech case study
#
# Product attribute classification with NLP
# The objective of this script is using NLP technologies for product attribute classification
#
# Author: Kai Chen
# Date: Apr, 2018
#

import sys

import pandas as pd
import numpy as np
from random import shuffle

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import seaborn as sns
# %matplotlib inline

from scipy.sparse import csr_matrix, hstack

from nltk.corpus import stopwords

from keras.preprocessing.text import text_to_word_sequence

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.feature_selection import SelectFromModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import roc_curve, auc, roc_auc_score


np.random.seed(42)

# ---------------------
# Define the file paths
PRODUCT_CSV_FILE = 'data/products.csv'
ATTRIBUTE_CSV_FILE = 'data/attributes.csv'

attribute_name_col_name = 'AttributeName'
attribute_value_col_name = 'AttributeValueName'
attribute_col_name = 'Attribute'
product_id_col_name = 'ProductId'
product_description_col_name = 'Description'

# -----------
# Step 1. Read and explore the data
df_product = pd.read_csv(PRODUCT_CSV_FILE)
# print(df_product.describe())
# print(df_product.head())
# print(df_product.shape)

df_attribute = pd.read_csv(ATTRIBUTE_CSV_FILE)
df_attribute[attribute_col_name] = df_attribute[attribute_name_col_name] + '-'  + df_attribute[attribute_value_col_name]
# print(df_attribute.head())
# print(df_attribute.shape)

df_product_attribute = pd.merge(df_product, df_attribute, on=[product_id_col_name])
#print(df_product_attribute.head())
#print(df_product_attribute.shape)
#print(df_product_attribute.columns)
#print(df_product_attribute.describe())

print('number of attributes: {}'.format(len(df_product_attribute[attribute_col_name].unique())))

list_product_id = df_attribute[product_id_col_name].unique()
print('number of products: {}'.format(len(list_product_id)))

# Create a dictionary, key: product id -> value: description
dict_product_des = dict()
for product_id in list_product_id:
    # we assume that one product has only one description.
    if product_id in dict_product_des:
        print('product {} has more than one description'.format(product_id))
    df_sub = df_product_attribute[df_product_attribute[product_id_col_name] == product_id]
    dict_product_des[product_id] = df_sub[product_description_col_name].values[0]


# Create a dictionary, key: attributes -> value: product id list
list_attribute = df_product_attribute[attribute_col_name].unique()
dict_attribute = dict()
dict_attribute_nb_products = dict()
for attribute in list_attribute:
    if attribute not in dict_attribute:
        dict_attribute[attribute] = []
    dict_attribute[attribute].append(df_product_attribute[df_product_attribute[attribute_col_name] == attribute][product_id_col_name].values)

nb_products_attribute = []
for attribute in list_attribute:
    dict_attribute_nb_products[attribute] = len(dict_attribute[attribute][0])
    nb_products_attribute.append(len(dict_attribute[attribute][0]))


# Get max and min number of products per attribute
min_products = sys.maxsize
min_products_attribute = ''
max_products = 0
max_products_attribute = ''
for category, nb_products in dict_attribute_nb_products.items():
    if nb_products < min_products:
        min_products = nb_products
        min_products_attribute = category
    if nb_products > max_products:
        max_products = nb_products
        max_products_cat = category

print('attribute {} has the max number of products, i.e., {}'.format(max_products_attribute, max_products))
print('attribute {} has the min number of products, i.e., {}'.format(min_products_attribute, min_products))
print('mean number of products per attribute: {}'.format(round(np.mean(nb_products_attribute), 2)))
print('standard deviation of number of products per attribute: {}'.format(round(np.std(nb_products_attribute), 2)))


# Create a dictionary, key: product id -> value: one-hot encoding list of attributes
list_attribute_value = df_attribute[attribute_col_name].unique()
dict_product_att = dict()
for product_id in list_product_id:
    # one-hot encoding list of attribute value name
    dict_product_att[product_id] = dict()
    for attribute in list_attribute_value:
        dict_product_att[product_id][attribute] = 0
    list_product_attribute = df_product_attribute[df_product_attribute[product_id_col_name] == product_id][attribute_col_name]
    for attribute in list_product_attribute:
        dict_product_att[product_id][attribute] = 1


# ---------
# Step 2: Prepare train and test sets
percentage_train_set = 0.7
shuffle(list_product_id)
list_product_id_train = list_product_id[0:int(percentage_train_set*len(list_product_id))]
list_product_id_test = list_product_id[len(list_product_id_train):]

print('number of samples: {}'.format(len(list_product_id)))
print('number of train samples: {}'.format(len(list_product_id_train)))
print('number of test samples: {}'.format(len(list_product_id_test)))


# -----------
# Step 4: NLP for attribute classification

class_names = list_attribute_value


# -----------------
# Prepare data sets

train_text = []
train_attribute = dict()

for class_name in class_names:
    train_attribute[class_name] = []

for product_id in list_product_id_train:
    train_text.append(dict_product_des[product_id])
    for class_name in class_names:
        train_attribute[class_name].append(dict_product_att[product_id][class_name])

test_text = []
test_attribute = dict()

for class_name in class_names:
    test_attribute[class_name] = []

for product_id in list_product_id_test:
    test_text.append(dict_product_des[product_id])
    for class_name in class_names:
        test_attribute[class_name].append(dict_product_att[product_id][class_name])

# -------------
# Remove stop words
def cleanupDoc(s):
    stopset = set(stopwords.words('english'))
    stopset.add('wikipedia')
    tokens = text_to_word_sequence(s, filters="\"!'#$%&()*+,-˚˙./:;‘“<=·>?@[]^_`{|}~\t\n", lower=True, split=" ")
    cleanup = " ".join(filter(lambda word: word not in stopset, tokens))
    return cleanup

train_text = [cleanupDoc(text) for text in train_text]
test_text = [cleanupDoc(text) for text in test_text]


# --------------
# Extract features
word_vectorizer = TfidfVectorizer(
    sublinear_tf=True,
    strip_accents='unicode',
    analyzer='word',
    token_pattern=r'\w{1,}',
    ngram_range=(1, 2),
    # max_features=50000,
    max_features=10000,
    )
train_word_features = word_vectorizer.fit_transform(train_text)
#print('Word TFIDF 1/2')
test_word_features = word_vectorizer.transform(test_text)
#print('Word TFIDF 2/2')

char_vectorizer = TfidfVectorizer(
    sublinear_tf=True,
    strip_accents='unicode',
    analyzer='char',
    stop_words='english',
    ngram_range=(2, 6),
    # max_features=50000,
    max_features=10000,
    )
train_char_features = char_vectorizer.fit_transform(train_text)
#print('Char TFIDF 1/2')
test_char_features = char_vectorizer.transform(test_text)
#print('Char TFIDF 2/2')

train_features = hstack([train_char_features, train_word_features])
#print('HStack 1/2')
test_features = hstack([test_char_features, test_word_features])
#print('HStack 2/2')

pred_attribute = dict()
dict_roc_auc_scores = dict()
dict_roc_auc_cv_scores = dict()

for class_name in class_names:
    train_target = train_attribute[class_name]

    if len(set(train_target)) > 1:
        classifier = LogisticRegression(solver='sag')
        sfm = SelectFromModel(classifier, threshold=0.2)

        train_sparse_matrix = sfm.fit_transform(train_features, train_target)
        # print(train_features.shape)
        # print(train_sparse_matrix.shape)

        # train_sparse_matrix, valid_sparse_matrix, y_train, y_valid = train_test_split(train_sparse_matrix, train_target,
        #                                                                               test_size=0.05, random_state=42)
        test_sparse_matrix = sfm.transform(test_features)

        if train_sparse_matrix.shape[1] <= 0:
            train_sparse_matrix = train_features
            test_sparse_matrix = test_features

        #cv_score = np.mean(cross_val_score(classifier, train_sparse_matrix, train_target, cv=2, scoring='roc_auc'))
        #dict_roc_auc_cv_scores[class_name] = cv_score
        #print('CV roc auc score for class {} is {}'.format(class_name, cv_score))

        classifier.fit(train_sparse_matrix, train_target)

        pred_attribute[class_name] = classifier.predict_proba(test_sparse_matrix)[:, 1]
        #pred_attribute[class_name] = classifier.predict(test_sparse_matrix)

        test_target = test_attribute[class_name]
        if (len(set(test_target)) > 1):
            score = roc_auc_score(test_target, pred_attribute[class_name])
            dict_roc_auc_scores[class_name] = score

        #print('test roc auc score for class {} is {}'.format(class_name, score))
    else:
        print('{} has only {} class sample'.format(class_name, len(set(train_target))))


for key, value in dict_roc_auc_scores.items():
    print(key)
    print(value)


# ---------
# Future work
# - Given a product description, predict the attribute values
# - Use word2vec as features
# - Try GRU or LSTM
# - Combine vision with text feature for attribute classification
