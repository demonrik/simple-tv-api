#!/bin/sh
# Simple shell script to automate the download script from STV
#
PYTHON_BIN=/usr/bin/python
PYTHON_OPTS=

STV_API_DIR=/share/Public/stv-api
STV_API_CFG=${STV_API_DIR}/stv-api.ini
STV_API_LOG=${STV_API_DIR}/stv.log
STV_API_LVL=debug
STV_API_STR=/share/Public/SimpleTV
STV_API_BIN=download.py

if [ "${STV_API_CFG}" != "" ]; then
    CONFIG="--config ${STV_API_CFG}"
fi

if [ "${STV_API_LOG}" != "" ]; then
    LOG="--logfile ${STV_API_LOG}"
fi

if [ "${STV_API_LVL}" != "" ]; then
    LOGLVL="--loglevel ${STV_API_LVL}"
fi

if [ "${STV_API_STR}" != "" ]; then
    STORE="--store ${STV_API_STR}"
fi

${PYTHON_BIN} ${PYTHON_OPTS} ${STV_API_DIR}/${STV_API_BIN} ${CONFIG} ${LOG} ${LOGLVL} ${STORE}
