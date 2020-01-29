# -*- coding: utf-8 -*-

"""
############################
CLASS : 'NORMAL', 'Map', 'YOUTUBE', 'WIKI', 'CALENDER', 'shopping', 'email', 'hotel', 'restaurant', 'CES', 'Flight'
####################
"""
import warnings

warnings.filterwarnings('ignore')

import tensorflow as tf
import numpy as np
import pickle
import getopt
import time
import sys
import os

from dnc.dnc import DNC
from recurrent_controller import RecurrentController

from grpc_wrapper.server import create_server, BaseModel




def linear(_input, _in_ch, _out_ch, _name):
    w = tf.get_variable(name='%s_w' % _name, shape=[_in_ch, _out_ch], dtype=tf.float32,
                        initializer=tf.contrib.layers.xavier_initializer())
    b = tf.get_variable(name='%s_b' % _name, shape=[_out_ch], dtype=tf.float32,
                        initializer=tf.constant_initializer(0.0))

    return tf.nn.bias_add(tf.matmul(_input, w), b)


def lstm(_current_input, _state, _name):
    dim_hidden = int(_state.get_shape()[-1] / 2)
    weight_matrix = tf.get_variable(_name, [dim_hidden + int(_current_input.get_shape()[-1]), 4 * dim_hidden],
                                    initializer=tf.contrib.layers.xavier_initializer())
    bf = tf.get_variable('lstm_bf_%s' % _name, [1, dim_hidden], initializer=tf.constant_initializer(1.0))
    bi = tf.get_variable('lstm_bi_%s' % _name, [1, dim_hidden], initializer=tf.constant_initializer(0.0))
    bo = tf.get_variable('lstm_bo_%s' % _name, [1, dim_hidden], initializer=tf.constant_initializer(0.0))
    bc = tf.get_variable('lstm_bc_%s' % _name, [1, dim_hidden], initializer=tf.constant_initializer(0.0))

    c, h = tf.split(_state, 2, 1)
    input_matrix = tf.concat([h, _current_input], 1)
    f, i, o, Ct = tf.split(tf.matmul(input_matrix, weight_matrix), 4, 1)
    f = tf.nn.sigmoid(f + bf)
    i = tf.nn.sigmoid(i + bi)
    o = tf.nn.sigmoid(o + bo)
    Ct = tf.nn.tanh(Ct + bc)
    new_c = f * c + i * Ct
    new_h = o * tf.nn.tanh(new_c)
    new_state = tf.concat([new_c, new_h], 1)

    return new_h, new_state


def llprint(message):
    sys.stdout.write(message)
    sys.stdout.flush()


def load(path):
    return pickle.load(open(path, 'rb'))


def onehot(index, size):
    vec = np.zeros(size, dtype=np.float32)
    vec[index] = 1.0
    return vec


def DNC_input_pre(input_data, word_space_size):
    input_vec = np.array(input_data, dtype=np.int32)
    seq_len = input_vec.shape[0]
    input_vec = np.array([onehot(code, word_space_size) for code in input_vec])
    return (
        np.reshape(input_vec, (1, -1, word_space_size)),
        seq_len)


def prepare_sample(sample, target_code, word_space_size):
    input_vec = np.array(sample[0]['inputs'], dtype=np.int32)
    seq_len = input_vec.shape[0]
    weights_vec = np.zeros(seq_len, dtype=np.float32)
    target_mask = (input_vec == target_code)
    output_vec = np.expand_dims(sample[0]['outputs'], 1)
    weights_vec[target_mask] = 1.0
    input_vec = np.array([onehot(code, word_space_size) for code in input_vec])

    return (
        np.reshape(input_vec, (1, -1, word_space_size)),
        output_vec,
        seq_len,
        np.reshape(weights_vec, (1, -1, 1))
    )


def inv_dict(dictionary):
    return {v: k for k, v in dictionary.iteritems()}


def mode_pre(input_data, word_space_size):
    print(input_data)
    mode_input =np.array(input_data, dtype=np.int32)
    input_vec = np.array([onehot(code, word_space_size) for code in mode_input])
    seq_len = input_vec.shape[0]

    return (
        np.reshape(input_vec, (1, -1, word_space_size)),
        seq_len)

if __name__ == '__main__':

    dirname = os.path.dirname(__file__)
    ckpts_dir = os.path.join(dirname, 'checkpoints')
    pkl_data_file = os.path.join(dirname, 'intention_2_19.pkl')
    ckpt_path = os.path.join(dirname, 'checkpoints/intent_SD_20190320/step-40000/model.ckpt')
    pkl_data = pickle.load(open(pkl_data_file, 'rb'))

    #train_data = pkl_data['train']

    inv_dictionary = pkl_data['idx2w']
    lexicon_dict = pkl_data['w2idx']
    target_class = len(pkl_data['class'])

    llprint("Loading Data ... ")

    # dncinput = np.load(input_file)

    inv_dictionary = idx2w = pkl_data['idx2w']

    llprint("Done!\n")

    batch_size = 1
    input_size = len(lexicon_dict)
    output_size = 512  ##autoencoder LSTM hidden unit dimension
    sequence_max_length = 100
    word_space_size = len(lexicon_dict)
    words_count = 256
    word_size = 128
    read_heads = 4

    iterations = 100000
    start_step = 0  ##woo

    options, _ = getopt.getopt(sys.argv[1:], '', ['checkpoint=', 'iterations=', 'start='])

    hidden_size = 512
    mlp_input = output_size
    llprint("Done!\n")

    for opt in options:
        if opt[0] == '--checkpoint':
            from_checkpoint = opt[1]
        elif opt[0] == '--iterations':
            iterations = int(opt[1])
        elif opt[0] == '--start':
            start_step = int(opt[1])

    graph = tf.Graph()
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    with graph.as_default():
        with tf.Session(graph=graph, config=config) as session:

            llprint("Building Computational Graph ... ")

            ncomputer = DNC(
                RecurrentController,
                input_size,
                output_size,
                sequence_max_length,
                words_count,
                word_size,
                read_heads,
                batch_size
            )

            output, _ = ncomputer.get_outputs()

            dec_target = tf.placeholder(tf.int32)

            target_onehot = tf.one_hot(dec_target, target_class)

            with tf.variable_scope('logit'):
                W_logit = tf.get_variable('W_logit', [output_size, target_class])
                b_logit = tf.get_variable('b_logit', [target_class])
                out_logit = tf.matmul(tf.expand_dims(output[0, -1, :], axis=0), W_logit) + b_logit

            #loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=out_logit, labels=target_onehot))

            #gradients = optimizer.compute_gradients(loss)

            llprint("Initializing Variables ... ")
            """
            ##세션 시작########################################################
            """

            session.run(tf.global_variables_initializer())
            llprint("Done!\n")
            var_list = tf.trainable_variables()
            saver = tf.train.Saver(var_list=var_list)
            print([v.name for v in tf.trainable_variables()])

            saver.restore(session, ckpt_path)

            last_100_losses = []

            start = 0 if start_step == 0 else start_step + 1
            end = start_step + iterations + 1

            start_time_100 = time.time()
            end_time_100 = None
            avg_100_time = 0.
            avg_counter = 0

            inputsen = []
            predsen = []
            lenth = 100

            overlap_num = 0
            before_out = []
            init_M = [
                np.ones([batch_size, words_count, word_size]) * 1e-6,
                np.zeros([batch_size, words_count]),
                np.zeros([batch_size, words_count]),
                np.zeros([batch_size, words_count, words_count]),
                np.ones([batch_size, words_count]) * 1e-6,
                np.ones([batch_size, words_count, read_heads]) * 1e-6,
                np.ones([batch_size, word_size, read_heads]) * 1e-6,

            ]

            def conversate(input_, m_count, memory_S):
                if memory_S == None:
                    New_memory = init_M
                else:
                    New_memory = memory_S

                if m_count == 10 :
                    New_memory = init_M
                    m_count =0

                x = input_["sentence"]
                #act_num = input_["act"]
                x= x.replace("'"," ' ")
                x = x.split(" ")

                user_num = []
                for tt in x:
                    try:
                        user_num.append(lexicon_dict[tt])
                    except KeyError:
                        user_num.append(lexicon_dict['<unk>'])

                user_num = user_num + [lexicon_dict["<go>"]]
                input_data, seq_len = mode_pre(user_num, word_space_size)
                outputvec, memory = session.run([
                    out_logit, ncomputer.check_memory
                ], feed_dict={
                    #dec_in: np.expand_dims(np.expand_dims(dec_input, axis=1), axis=0),
                    ncomputer.input_data: input_data,
                    ncomputer.sequence_length: seq_len,
                    ncomputer.m_0: New_memory[0],
                    ncomputer.m_1: New_memory[1],
                    ncomputer.m_2: New_memory[2],
                    ncomputer.m_3: New_memory[3],
                    ncomputer.m_4: New_memory[4],
                    ncomputer.m_5: New_memory[5],
                    ncomputer.m_6: New_memory[6],
                })
                intent_list = pkl_data['class']
                New_memory = memory
                pred_index = outputvec[0].argmax()
                pred_sent = ("%s\t%4f" %(intent_list[pred_index],outputvec[0][pred_index]))

                return pred_sent.replace('<unk>', ','), m_count+1, New_memory

            class Generator(BaseModel):
                def __init__(self, m_count = 0):
                    self.m_count = m_count
                    self.before_sentence = ""
                    self.memory_S = None
                    print("init")

                def send(self, input):
                    result, self.m_count, self.memory_S = conversate(input, self.m_count, self.memory_S)

                    return {"output": str(result)}


            def run():
                port = int(sys.argv[1])
                # port = 40003

                model = Generator()

                server = create_server(model, ip="[::]", port=port)
                server.start()
                try:
                    while True:
                        time.sleep(60 * 60 * 24)
                except KeyboardInterrupt:
                    server.stop(0)


            run()
