# -*- coding: utf-8 -*-

# Try bulk write to elasticsearch database
# - try check the return of helpers.bulk()
# - after this check,
# TODO: Modify the code in LanZou to check the document lost when write to ES

import time
import json
import pandas as pd
from elasticsearch import Elasticsearch, helpers
from datetime import datetime, timedelta

def avg_by_ts(es_host, es_port, es_user, es_pwd, data_index, start, end,field):
    client = Elasticsearch(host=es_host, port=es_port, http_auth=(es_user, es_pwd))

    resp = client.search(
        index = data_index,
        body = {
            "query":{
                "range":{
                    "createdAt":{
                        "gte": start,
                        "lt": end
                    }
                }
            },
            "size":0,
            "aggs":{
                "result":{
                    "date_histogram":{
                        "field": "createdAt",
                        "interval": "hour",
                        "format":"yyyy-MM-dd HH:mm:ss"
                    },
                    "aggs":{
                        "stat_value":{
                            "avg": { "field": field }
                        }
                    }
                }
            }
        }
    )
    lines = []
    for item in resp['aggregations']['result']['buckets']:
        line = {
            'createdAt': datetime.fromtimestamp(item['key']/1000),
            'doc_cnt': item['doc_count'],
            'ts': item['key_as_string'],
            'value':item['stat_value']['value']
        }
        lines.append(line)

    data_frame = pd.DataFrame(lines)
    # !!! the columns order will follow the first char of the field name above
    data_frame.columns=["createdAt","doc_cnt","dateTime","value"]
    data_frame["cleanvalue"]=data_frame["value"].interpolate()
    print (data_frame.head(10))
    return data_frame


def writer_bulk(host, port, es_user, es_pwd, df, ES_index):
    es=Elasticsearch(host=host, port=port, http_auth=(es_user, es_pwd))

    tmp = df.to_json(orient = "records",date_format="iso")
    df_json = json.loads(tmp)
    actions = []
    for row in df_json:
        actions.append({
           "_op_type": "index",
           "_index": ES_index,
           "_type": "data",
           "_source": row
        })
        if len(actions) == 100:
            successCnt, errorList = helpers.bulk(
                es,
                actions,
                stats_only=False,
                index=ES_index,
                doc_type="data",
                request_timeout=60)
            print('successCnt : ', successCnt)
            print('errorList: ', errorList)
            actions = []

    #write the rest
    successCnt, errorList = helpers.bulk(
        es,
        actions,
        stats_only=False,
        index=ES_index,
        doc_type="data",
        request_timeout=60)
    print('successCnt : ', successCnt)
    print('errorList: ', errorList)


if __name__=="__main__":

    startTimeStamp = datetime(2019, 4, 23, 18, 0, 0, 0)
    endTimeStamp = datetime(2019, 4, 24, 18, 10, 0, 0)

    esHost = '192.168.0.20'
    esPort = 9200
    esUser = 'elastic'
    esPwd = 'd2VsY29tZTEK'

    avg_df = avg_by_ts(
        esHost,
        esPort,
        esUser,
        esPwd,
        'alert_core_total_count*',
        startTimeStamp,
        endTimeStamp,
        'info.value'
    )

    writer_bulk(
        esHost,
        esPort,
        esUser,
        esPwd,
        avg_df,
        'leiw_test_avg_totalcnt'
    )
