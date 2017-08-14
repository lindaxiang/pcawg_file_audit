import os
import sys
import click
import util
from elasticsearch import Elasticsearch
from collections import OrderedDict

es_queries = [
    #query 0: summary for each repo
    {
        "query": {
            "bool": {
                "must" : [
                  {
                    "match" : { "is_in_pcawg_v1_4" : "true" }
                    }
                ],
                "must_not":[ 
                  {
                    "match" : { "file_format" : "Other" }
                    }
                  ]
            }
        },
        "aggs" : {
            "repos" : {
                "terms" : { "field" : "file_copies.repo_name.keyword" },
                "aggs" : {
                    "analysis_softwares" : { "terms" : { "field" : "analysis_software.keyword" } }
                }
            }
        }
    },
    #query 1: summary for US projects

    {
        "query": {
            "bool": {
                "must" : [
                  {
                    "match" : { "is_in_pcawg_v1_4" : "true" }
                    },
                  {
                    "match": {
                      "dcc_project_code": "*-US"
                    }
                  }
                ],
                "must_not":[ 
                  {
                    "match" : { "file_format" : "Other" }
                    }
                  ]
        }
      },
        "aggs" : {
                    "analysis_softwares" : { "terms" : { "field" : "analysis_software.keyword" } }
                }
    },
    #query 2: summary for Non-US projects
    {
        "query": {
            "bool": {
                "must" : [
                  {
                    "match" : { "is_in_pcawg_v1_4" : "true" }
                    }
                ],
                "must_not":[ 
                  {
                    "match" : { "file_format" : "Other" }
                    },
                  {
                    "match": {
                      "dcc_project_code": "*-US"
                    }
                  }
                  ]
        }
      },
        "aggs" : {
                    "analysis_softwares" : { "terms" : { "field" : "analysis_software.keyword" } }
                }
    },

    #query 3: summary for all projects
        {
        "query": {
            "bool": {
                "must" : [
                  {
                    "match" : { "is_in_pcawg_v1_4" : "true" }
                    }
                ],
                "must_not":[ 
                  {
                    "match" : { "file_format" : "Other" }
                    }
                  ]
        }
      },
        "aggs" : {
                    "analysis_softwares" : { "terms" : { "field" : "analysis_software.keyword" } }
                }
    },    

    #query 4: summary for the projects which are allowed to transfer to AWS
        {
        "query": {
            "bool": {
                "must" : [
                  {
                    "match" : { "is_in_pcawg_v1_4" : "true" }
                    }
                ],
                "must_not":[ 
                  {
                    "match" : { "file_format" : "Other" }
                    }
                  ],
                "filter":{
                   "terms":{
                      "dcc_project_code.keyword": ["LIRI-JP","PACA-CA","PRAD-CA","RECA-EU","PAEN-AU","PACA-AU","BOCA-UK","OV-AU","MELA-AU","BRCA-UK","PRAD-UK","CMDI-UK","LINC-JP","ORCA-IN","BTCA-SG","LAML-KR","LICA-FR","CLLE-ES","ESAD-UK", "PAEN-IT"]
                   }
            }
        }
      },
        "aggs" : {
                    "analysis_softwares" : { "terms" : { "field" : "analysis_software.keyword" } }
                }
    },     
]


def generate_overall(app_ctx):
    # queries to generate the reports
    # generate the overall reports for the repos
    schema = app_ctx['input_schemas']['fileobject']

    es_index_name = app_ctx['config']['es.index_name']
    response = app_ctx['es'].search(index=es_index_name, body=es_queries[0])
    report_filename = os.path.join(app_ctx['output_dir'], schema['overall_report_file_name'])
    report = generate_report(response)
    # add us projects count
    response = app_ctx['es'].search(index=es_index_name, body=es_queries[1])
    report = add_report(response, report, 'US-total')
    # add non-us projects count
    response = app_ctx['es'].search(index=es_index_name, body=es_queries[2])
    report = add_report(response, report, 'Non-US total')
    # add all projects count
    response = app_ctx['es'].search(index=es_index_name, body=es_queries[3])
    report = add_report(response, report, 'Total')
    write_report(report, report_filename)
    # add AWS projects count
    response = app_ctx['es'].search(index=es_index_name, body=es_queries[4])
    report = add_report(response, report, 'Allow_to_AWS')
    write_report(report, report_filename)

def generate_report(response):
    report = OrderedDict()
    for r in ['gnos_osdc-tcga', 'gnos_osdc-icgc', 'gnos_ebi', 'gnos_bsc', 'gnos_dkfz', 'gnos_riken', 'US-total', 'Non-US total', 'Total', 'Allow_to_AWS', 'collab', 'aws', 'pdc', 'ega', 'dcc_portal']:
        report[r] = OrderedDict()
        for a in ['BWA MEM', 'TopHat2', 'STAR', 'Sanger variant call pipeline', 'DKFZ/EMBL variant call pipeline', 'Broad variant call pipeline', 'Muse variant call pipeline', 'PCWAG SNV-MNV callers', 'PCWAG InDel callers', 'Total']:
            report[r][a] = 0

    for p in response['aggregations']['repos'].get('buckets'):
        count = p.get('doc_count')
        repo = p.get('key')
        
        for a in p['analysis_softwares'].get('buckets'):
            software = a.get('key')
            doc_count = a.get('doc_count')
            report[repo][software] = doc_count

        report[repo]['Total'] = count

    # # generate the US-total
    # for a in ['BWA MEM', 'TopHat2', 'STAR', 'Sanger variant call pipeline', 'DKFZ/EMBL variant call pipeline', 'Broad variant call pipeline', 'Muse variant call pipeline', 'PCWAG SNV-MNV callers', 'PCWAG InDel callers']:
    #     report['US-total'][a] = report['gnos_osdc-tcga'][a]
    return report

def add_report(response, report, col):
    for p in response['aggregations']['analysis_softwares'].get('buckets'):
        count = p.get('doc_count')
        software = p.get('key')

        report[col][software] = count

    report[col]['Total'] = response['hits']['total']

    return report    


def write_report(report, report_filename):
    with open(report_filename, 'w') as f:
        
        header = '#analysis_softwares' + '\t' + '\t'.join(report.keys()) + '\n'
        f.write(header)
        
        for a in ['BWA MEM', 'TopHat2', 'STAR', 'Sanger variant call pipeline', 'DKFZ/EMBL variant call pipeline', 'Broad variant call pipeline', 'Muse variant call pipeline', 'PCWAG SNV-MNV callers', 'PCWAG InDel callers', 'Total']:
            line = a
            for r in ['gnos_osdc-tcga', 'gnos_osdc-icgc', 'gnos_ebi', 'gnos_bsc', 'gnos_dkfz', 'gnos_riken', 'US-total', 'Non-US total', 'Total', 'Allow_to_AWS', 'collab', 'aws', 'pdc', 'ega', 'dcc_portal']:
                line = line + '\t' + str(report[r][a])
            line = line + '\n'
            f.write(line)
    
    return 0
