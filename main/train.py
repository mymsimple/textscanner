from network.model import TextScannerModel,localization_map_loss
from utils.sequence import SequenceData
from utils import util, logger as log,label_utils
from tensorflow.keras.callbacks import TensorBoard, ModelCheckpoint,EarlyStopping
from tensorflow.keras.models import load_model
from tensorflow.keras.optimizers import Adam
import conf
import os
import logging
import tensorflow as tf
from tensorflow.keras import Input
logger = logging.getLogger(__name__)


def train(args):
    charset = label_utils.get_charset(conf.CHARSET)
    conf.CHARSET_SIZE = len(charset)

    model = TextScannerModel(conf,charset)
    losses =['categorical_crossentropy','categorical_crossentropy',localization_map_loss()]
    loss_weights = [1,10,10] # weight value refer from paper
    model.compile(Adam(),loss=losses,loss_weights=loss_weights,metrics=['accuracy'],run_eagerly=True)

    train_sequence = SequenceData(name="Train",
                                  label_dir=args.train_label_dir,
                                  label_file=args.train_label_file,
                                  charsets=charset,
                                  conf=conf,
                                  args=args,
                                  batch_size=args.batch)
    valid_sequence = SequenceData(name="Validate",
                                  label_dir=args.validate_label_dir,
                                  label_file=args.validate_label_file,
                                  charsets=charset,
                                  conf=conf,
                                  args=args,
                                  batch_size=args.validation_batch)

    timestamp = util.timestamp_s()
    tb_log_name = os.path.join(conf.DIR_TBOARD, timestamp)
    # checkpoint_path = conf.DIR_MODEL + "/model-" + timestamp + "-epoch{epoch:03d}-acc{accuracy:.4f}-val{val_accuracy:.4f}.hdf5"
    checkpoint_path = conf.DIR_MODEL + "/model-" + timestamp + "-epoch{epoch:03d}.hdf5"

    # 如果checkpoint文件存在，就加载之
    if args.retrain:
        logger.info("重新开始训练....")
    else:
        logger.info("基于之前的checkpoint训练...")
        _checkpoint_path = util.get_checkpoint(conf.DIR_CHECKPOINT)
        if _checkpoint_path is not None:
            model = load_model(_checkpoint_path)
            logger.info("加载checkpoint模型[%s]", _checkpoint_path)
        else:
            logger.warning("找不到任何checkpoint，重新开始训练")

    logger.info("Begin train开始训练：")

    tboard = TensorBoard(log_dir=tb_log_name,histogram_freq=1,batch_size=2,write_grads=True)
    early_stop = EarlyStopping(monitor='val_acc', patience=args.early_stop, verbose=1, mode='max')
    checkpoint = ModelCheckpoint(filepath=checkpoint_path, verbose=1, mode='max')

    # input = Input(shape=(64, 256,3), dtype=tf.float32)
    # model.build(input.shape)
    # model.summary()
    # tf.executing_eagerly()

    model.fit(
        x=train_sequence,
        steps_per_epoch=args.steps_per_epoch,#其实应该是用len(train_sequence)，但是这样太慢了，所以，我规定用一个比较小的数，比如1000
        epochs=args.epochs,
        workers=args.workers,   # 同时启动多少个进程加载
        callbacks=[tboard,checkpoint,early_stop],
        use_multiprocessing=True,
        validation_data=valid_sequence,
        validation_steps=args.validation_steps,
        verbose=2)

    model.summary()

    logger.info("Train end训练结束!")

    model_path = conf.DIR_MODEL + "/textscanner-{}.hdf5".format(util.timestamp_s())
    model.save(model_path)
    logger.info("Save model保存训练后的模型到：%s", model_path)

if __name__ == "__main__":
    log.init()
    args = conf.init_args()
    train(args)