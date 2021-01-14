# coding: utf-8
import unittest
import os
import base64
import numpy as np
from numpy.testing import assert_almost_equal
from onnx import helper, onnx_pb as onnx_proto
import onnxruntime as _ort
from onnxruntime_customops import (
    onnx_op, PyCustomOpDef,
    get_library_path as _get_library_path)
import tensorflow as tf
from tensorflow_text import SentencepieceTokenizer


"""
make_node(
    'RaggedTensorToSparse',
    inputs=['StatefulPartitionedCall/text_preprocessor/SentenceTokenizer/SentencepieceTokenizeOp:1',
            'StatefulPartitionedCall/text_preprocessor/SentenceTokenizer/SentencepieceTokenizeOp:0'],
    outputs=[
        'StatefulPartitionedCall/text_preprocessor/RaggedToSparse/RaggedTensorToSparse:0',
        'StatefulPartitionedCall/text_preprocessor/RaggedToSparse/RaggedTensorToSparse:1',
        'StatefulPartitionedCall/text_preprocessor/RaggedToSparse/RaggedTensorToSparse:2',
    ],
    name='StatefulPartitionedCall/text_preprocessor/RaggedToSparse/RaggedTensorToSparse',
    domain='ai.onnx.contrib',
    RAGGED_RANK=1,
    Tsplits=7,
),
"""


def load_piece(name):
    fullname = os.path.join(
        os.path.dirname(__file__), "data",
        "%s_%s.txt" % (
            os.path.splitext(os.path.split(__file__)[-1])[0],
            name))
    with open(fullname, "r") as f:
        return f.read()


def _create_test_model_sentencepiece(prefix, domain='ai.onnx.contrib'):
    nodes = []
    nodes.append(helper.make_node(
        '%sSentencepieceTokenizer' % prefix,
        inputs=[
            'model',  # model__6
            'inputs',  # inputs
            'nbest_size',
            'alpha',
            'add_bos',
            'add_eos',
            'reverse',
        ],
        outputs=['out0', 'out1'],
        name='SentencepieceTokenizeOpName',
        domain='ai.onnx.contrib',
    ))

    mkv = helper.make_tensor_value_info
    graph = helper.make_graph(
        nodes, 'test0', [
            mkv('model', onnx_proto.TensorProto.STRING, [None]),
            mkv('inputs', onnx_proto.TensorProto.STRING, [None]),
            mkv('nbest_size', onnx_proto.TensorProto.FLOAT, [None]),
            mkv('alpha', onnx_proto.TensorProto.FLOAT, [None]),
            mkv('add_bos', onnx_proto.TensorProto.BOOL, [None]),
            mkv('add_eos', onnx_proto.TensorProto.BOOL, [None]),
            mkv('reverse', onnx_proto.TensorProto.BOOL, [None])
        ], [
            mkv('out0', onnx_proto.TensorProto.INT32, [None]),
            mkv('out1', onnx_proto.TensorProto.INT64, [None])
        ])
    model = helper.make_model(
        graph, opset_imports=[helper.make_operatorsetid(domain, 1)])
    return model


def _create_test_model_ragged_to_sparse(prefix, domain='ai.onnx.contrib'):
    nodes = []
    nodes.append(helper.make_node(
        '%sSentencepieceTokenizer' % prefix,
        inputs=[
            'model',  # model__6
            'inputs',  # inputs
            'nbest_size',
            'alpha',
            'add_bos',
            'add_eos',
            'reverse',
        ],
        outputs=['tokout0', 'tokout1'],
        name='SentencepieceTokenizeOpName',
        domain='ai.onnx.contrib',
    ))
    nodes.append(helper.make_node(
        '%sRaggedTensorToSparse' % prefix,
        inputs=['tokout1', 'tokout0'],
        outputs=['out0', 'out1', 'out2'],
        name='RaggedTensorToSparse',
        domain='ai.onnx.contrib',
    ))

    mkv = helper.make_tensor_value_info
    graph = helper.make_graph(
        nodes, 'test0', [
            mkv('model', onnx_proto.TensorProto.STRING, [None]),
            mkv('inputs', onnx_proto.TensorProto.STRING, [None]),
            mkv('nbest_size', onnx_proto.TensorProto.FLOAT, [None]),
            mkv('alpha', onnx_proto.TensorProto.FLOAT, [None]),
            mkv('add_bos', onnx_proto.TensorProto.BOOL, [None]),
            mkv('add_eos', onnx_proto.TensorProto.BOOL, [None]),
            mkv('reverse', onnx_proto.TensorProto.BOOL, [None])
        ], [
            mkv('out0', onnx_proto.TensorProto.INT64, [None]),
            mkv('out1', onnx_proto.TensorProto.INT32, [None]),
            mkv('out2', onnx_proto.TensorProto.INT64, [None])
        ])
    model = helper.make_model(
        graph, opset_imports=[helper.make_operatorsetid(domain, 1)])
    return model


class TestPythonOpSentencePiece(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        @onnx_op(op_type="PySentencepieceTokenizer",
                 inputs=[PyCustomOpDef.dt_string,  # 0: model
                         PyCustomOpDef.dt_string,  # 1: input
                         PyCustomOpDef.dt_float,  # 2: nbest_size
                         PyCustomOpDef.dt_float,  # 3: alpha
                         PyCustomOpDef.dt_bool,  # 4: add_bos
                         PyCustomOpDef.dt_bool,  # 5: add_eos
                         PyCustomOpDef.dt_bool],  # 6: reverse
                 outputs=[PyCustomOpDef.dt_int32,
                          PyCustomOpDef.dt_int64])
        def sentence_piece_tokenizer_op(model, inputs, nbest_size,
                                        alpha, add_bos, add_eos, reverse):
            """Implements `text.SentencepieceTokenizer
            <https://github.com/tensorflow/text/blob/master/docs/
            api_docs/python/text/SentencepieceTokenizer.md>`_."""
            # The custom op implementation.
            tokenizer = SentencepieceTokenizer(
                base64.decodebytes(model[0].encode()),
                reverse=reverse[0],
                add_bos=add_bos[0],
                add_eos=add_eos[0],
                alpha=alpha[0],
                nbest_size=nbest_size[0])
            ragged_tensor = tokenizer.tokenize(inputs)
            output_values = ragged_tensor.flat_values.numpy()
            output_splits = ragged_tensor.nested_row_splits[0].numpy()
            return output_values, output_splits

        cls.SentencepieceTokenizer = sentence_piece_tokenizer_op

        @onnx_op(op_type="PyRaggedTensorToSparse",
                 inputs=[PyCustomOpDef.dt_int64,
                         PyCustomOpDef.dt_int32],
                 outputs=[PyCustomOpDef.dt_int64,
                          PyCustomOpDef.dt_int32,
                          PyCustomOpDef.dt_int64])
        def ragged_tensor_to_sparse(nested_splits, dense_values):
            sparse_indices, sparse_values, sparse_dense_shape = \
                tf.raw_ops.RaggedTensorToSparse(
                    rt_nested_splits=[nested_splits],
                    rt_dense_values=dense_values)
            return (sparse_indices.numpy(),
                    sparse_values.numpy(),
                    sparse_dense_shape.numpy())

        cls.RaggedTensorToSparse = ragged_tensor_to_sparse

    def test_string_sentencepiece_tokenizer_python(self):
        so = _ort.SessionOptions()
        so.register_custom_ops_library(_get_library_path())
        onnx_model = _create_test_model_sentencepiece('Py')
        self.assertIn('op_type: "PySentencepieceTokenizer"', str(onnx_model))
        sess = _ort.InferenceSession(onnx_model.SerializeToString(), so)

        for alpha in [0, 0.5]:
            for nbest_size in [0, 0.5]:
                for bools in range(0, 8):
                    with self.subTest(
                            alpha=alpha, nbest_size=nbest_size, bools=bools):
                        inputs = dict(
                            model=np.array(
                                [load_piece('model__6')], dtype=np.object),
                            inputs=np.array(
                                ["Hello world", "Hello world louder"],
                                dtype=np.object),
                            nbest_size=np.array(
                                [nbest_size], dtype=np.float32),
                            alpha=np.array([alpha], dtype=np.float32),
                            add_bos=np.array([bools & 1], dtype=np.bool_),
                            add_eos=np.array([bools & 2], dtype=np.bool_),
                            reverse=np.array([bools & 4], dtype=np.bool_))
                        txout = sess.run(None, inputs)

                        exp = self.SentencepieceTokenizer(**inputs)
                        for i in range(0, 2):
                            assert_almost_equal(exp[i], txout[i])

    def test_string_ragged_string_to_sparse_python(self):
        so = _ort.SessionOptions()
        so.register_custom_ops_library(_get_library_path())
        onnx_model = _create_test_model_ragged_to_sparse('Py')
        self.assertIn('op_type: "PyRaggedTensorToSparse"', str(onnx_model))
        sess = _ort.InferenceSession(onnx_model.SerializeToString(), so)

        inputs = dict(
            model=np.array([load_piece('model__6')], dtype=np.object),
            inputs=np.array(
                ["Hello world", "Hello world louder"], dtype=np.object),
            nbest_size=np.array([0], dtype=np.float32),
            alpha=np.array([0], dtype=np.float32),
            add_bos=np.array([0], dtype=np.bool_),
            add_eos=np.array([0], dtype=np.bool_),
            reverse=np.array([0], dtype=np.bool_))
        txout = sess.run(None, inputs)
        temp = self.SentencepieceTokenizer(**inputs)
        exp = self.RaggedTensorToSparse(temp[1], temp[0])
        for i in range(0, 3):
            assert_almost_equal(exp[i], txout[i])


if __name__ == "__main__":
    unittest.main()
