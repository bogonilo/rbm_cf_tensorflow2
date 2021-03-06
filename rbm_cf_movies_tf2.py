import tensorflow as tf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

pd.options.display.width = 0

movies_df = pd.read_csv('ml-1m/movies.dat', sep='::', header=None, engine='python')
ratings_df = pd.read_csv('ml-1m/ratings.dat', sep='::', header=None, engine='python')
movies_df.columns = ['MovieID', 'Title', 'Genres']
ratings_df.columns = ['UserID', 'MovieID', 'Rating', 'Timestamp']

user_rating_df = ratings_df.pivot(index='UserID', columns='MovieID', values='Rating')
norm_user_rating_df = user_rating_df.fillna(0) / 5.0
trX = norm_user_rating_df.values
trX = tf.cast(trX, dtype=tf.float32)

hiddenUnits = 20
visibleUnits = len(user_rating_df.columns)
alpha = 1.0

#Phase 1: Input Processing
def draw_sample_h0(v0, W, hb): #h0
    h0_prob = tf.nn.sigmoid(tf.matmul(v0, W) + hb)
    return tf.nn.relu(tf.sign(h0_prob - tf.random.uniform(tf.shape(h0_prob)))) # drawing a sample from the distribution

#Phase 2: Reconstruction
def draw_sample_v1(h0, W, vb): #v1
    v1_prob = tf.nn.sigmoid(tf.matmul(h0, tf.transpose(W)) + vb)
    return tf.nn.relu(tf.sign(v1_prob - tf.random.uniform(tf.shape(v1_prob)))) # sampling from visible units distribution

def calculate_h1(v1, W, hb): #h1
    return tf.nn.sigmoid(tf.matmul(v1, W) + hb) # correspondent hidden units

# Calculate Contrastive Divergence
def calculate_CD(v0, h0, v1, h1): #CD
    w_pos_grad = tf.matmul(tf.transpose(v0), h0)
    w_neg_grad = tf.matmul(tf.transpose(v1), h1)
    # Calculate the Contrastive Divergence to maximize
    return (w_pos_grad - w_neg_grad) / tf.cast(tf.shape(v0)[0], dtype=tf.float32)

# Calculate reconstruction error
def calculate_error_sum(v0, v1): #err_sum
    err = v0 - v1
    return tf.reduce_mean(err * err)

"""Variable initialisations"""
#Current weight
cur_w = np.zeros([visibleUnits, hiddenUnits], np.float32)
#Current visible unit biases
cur_vb = np.zeros([visibleUnits], np.float32)
#Current hidden unit biases
cur_hb = np.zeros([hiddenUnits], np.float32)
#Previous weight
prv_w = np.zeros([visibleUnits, hiddenUnits], np.float32)
#Previous visible unit biases
prv_vb = np.zeros([visibleUnits], np.float32)
#Previous hidden unit biases
prv_hb = np.zeros([hiddenUnits], np.float32)

epochs = 15
batchsize = 100
errors = []
for i in range(epochs):
    for start, end in zip( range(0, len(trX), batchsize), range(batchsize, len(trX), batchsize)):
        batch = trX[start:end]
        v0 = batch
        h0 = draw_sample_h0(v0, cur_w, cur_hb)
        v1 = draw_sample_v1(h0, cur_w, cur_vb)
        h1 = calculate_h1(v1, cur_w, cur_hb)
        CD = calculate_CD(v0,h0,v1,h1)
        cur_w = prv_w + alpha * CD
        cur_vb = prv_vb + alpha * tf.reduce_mean(v0 - v1, 0)
        cur_hb = prv_hb + alpha * tf.reduce_mean(h0 - h1, 0)
        prv_w = cur_w
        prv_vb = cur_vb
        prv_hb = cur_hb
    errors.append(calculate_error_sum(trX, draw_sample_v1(draw_sample_h0(trX, cur_w, cur_hb), cur_w, cur_vb)))
    print (errors[-1])
plt.plot(errors)
plt.ylabel('Error')
plt.xlabel('Epoch')
plt.show()

#Selecting the input user
mock_user_id = 215
inputUser = tf.reshape(trX[mock_user_id-1], [1, -1])

#Feeding in the user and reconstructing the input
feed = tf.nn.sigmoid(tf.matmul(inputUser, prv_w) + prv_hb)
rec = tf.nn.sigmoid(tf.matmul(feed, tf.transpose(prv_w)) + prv_vb)
# print(rec)

scored_movies_df_mock = movies_df[movies_df['MovieID'].isin(user_rating_df.columns)]
scored_movies_df_mock = scored_movies_df_mock.assign(RecommendationScore = rec[0])
# print(scored_movies_df_mock.sort_values(["RecommendationScore"], ascending=False).head(20))

movies_df_mock = ratings_df[ratings_df['UserID'] == mock_user_id]

#Merging movies_df with ratings_df by MovieID
merged_df_mock = scored_movies_df_mock.merge(movies_df_mock, on='MovieID', how='outer')

print(merged_df_mock.sort_values(["RecommendationScore"], ascending=False).head(20))

