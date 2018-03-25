import psycopg2
import sqlite3
import pandas as pd
import numpy as np
import toolz.curried
from typing import List

import os
import sys

if os.getenv('MY_PYTHON_PKG') not in sys.path:
    sys.path.append(os.getenv('MY_PYTHON_PKG'))

import syspath
from common.connection import conn_local_lite, conn_local_pg
import dftosql
import sqlCommand as sqlc
from sqliteToPostgres.update import utils


conn_lite = conn_local_lite('tse.sqlite3')
conn_pg = conn_local_pg('tse')
cur = conn_pg.cursor()
curLite = conn_lite.cursor()

table = '外資及陸資買賣超彙總表 (股)'

columns = list(pd.read_sql_query("SELECT * FROM '{}' limit 1".format(table), conn_lite))
date_columns = ['年月日']
varchar_columns = ['證券代號', '證券名稱']
integer_columns = list(filter(lambda x: x not in (date_columns + varchar_columns), columns))
types = {'date': date_columns, 'str': varchar_columns, 'int': integer_columns}
cols = ['年月日']

rows1 = toolz.compose(utils.to_dict, utils.as_type(types), sqlc.s_dist_lite(conn_lite, table))(cols)
rows2 = toolz.compose(utils.to_dict, utils.as_type(types), sqlc.s_dist_pg(conn_pg, table))(cols)
rows = utils.diff(rows1, rows2)


@toolz.curry
def transform(dtypes: dict, df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={'買進股數': '外資買進股數', '賣出股數': '外資賣出股數', '買賣超股數': '外資買賣超股數', '鉅額交易': '外資鉅額交易'}).replace('--',np.nan).replace('NaN', 0).fillna(0)
    df[['外資鉅額交易']] = df[['外資鉅額交易']].applymap(lambda x: 0 if x == ' ' else 1)
    df = utils.as_type(dtypes, df)
    return df


def read_insert(row: list) -> List:
    return toolz.compose(dftosql.i_pg_batch(conn_pg, table), transform(types), sqlc.s_where_lite(conn_lite, table))(row)


list(map(read_insert, rows))
