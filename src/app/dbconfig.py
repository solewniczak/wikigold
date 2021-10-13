from flask import g
from app.db import get_db


def load_dbconfig():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    sql_select_config = "SELECT `key`, `value`, `type` FROM `config`"
    cursor.execute(sql_select_config)

    dbconfig = {}
    for result in cursor:
        if result['type'] == 'int':
            dbconfig[result['key']] = int(result['value'])
        else:
            dbconfig[result['key']] = result['value']

    cursor.close()
    g.dbconfig = dbconfig

def get_dbconfig(key=None):
    if 'dbconfig' not in g:
        load_dbconfig()

    if key is None:
        return g.dbconfig
    else:
        return g.dbconfig[key]


def update_dbconfig(new_config_dict):
    db = get_db()
    cursor = db.cursor()
    dbconfig = get_dbconfig()

    for key, value in new_config_dict.items():
        if key in dbconfig:
            sql_update_config = "UPDATE `config` SET `value`=%s WHERE `key`=%s"
            data_config = (value, key)
            cursor.execute(sql_update_config, data_config)
    db.commit()
    load_dbconfig()
