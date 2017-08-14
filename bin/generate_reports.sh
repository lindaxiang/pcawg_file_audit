#!/bin/bash

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd $DIR

output_dir='../examples/file_auditing/output'

# generate the list of files missing from Collab
header="dcc_project_code\tanalysis_software\tgnos_id\tfile_name\tfile_object_id\tdonor_wgs_exclusion_white_gray"
echo -e $header > $output_dir/collab_missing_files.txt
curl --user elastic:changeme -XGET "http://localhost:9200/pcawg-r1/file_object/_search?size=3000" -d '{
    "_source": ["file_object_id", "gnos_id", "dcc_project_code", "file_name", "donor_wgs_exclusion_white_gray", "analysis_software"],
    "query": {
        "bool": {
            "must" : [
              {
                "match" : { "is_in_pcawg_v1_4" : "true" }
                }  
            ],
            "must_not":[ 
              {
                "match": {
                    "file_copies.repo_name": "collab"
                }
              },
              {
                "match": {
                  "dcc_project_code": "*-US"
                }
              },
              {
                "match" : { "file_format" : "Other" }
                }
            ]
          }
    },
    "sort" : [
        { "analysis_software.keyword" : {"order" : "desc"}},
        { "dcc_project_code.keyword" : {"order" : "asc"} },
        "_score"
    ]
}
' | jq -r '.hits.hits[]._source | [.dcc_project_code, .analysis_software, .gnos_id, .file_name, .file_object_id, .donor_wgs_exclusion_white_gray] | join("\t")' >> $output_dir/collab_missing_files.txt

# generate the list of files missing from AWS
echo -e $header > $output_dir/aws_missing_files.txt
curl --user elastic:changeme -XGET "http://localhost:9200/pcawg-r1/file_object/_search?size=3000" -d '{
    "_source": ["file_object_id", "gnos_id", "dcc_project_code", "file_name", "donor_wgs_exclusion_white_gray", "analysis_software"],
    "query": {
        "bool": {
            "must" : [
              {
                "match" : { "is_in_pcawg_v1_4" : "true" }
                }  
            ],
            "must_not":[ 
              {
                "match": {
                    "file_copies.repo_name": "aws"
                }
              },
              {
                "match": {
                  "dcc_project_code": "*-US"
                }
              },
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
    "sort" : [
        { "analysis_software.keyword" : {"order" : "desc"}},
        { "dcc_project_code.keyword" : {"order" : "asc"} },
        "_score"
    ]
}' | jq -r '.hits.hits[]._source | [.dcc_project_code, .analysis_software, .gnos_id, .file_name, .file_object_id, .donor_wgs_exclusion_white_gray] | join("\t")' >> $output_dir/aws_missing_files.txt

# generate the list of index files missing from Collab
echo -e $header > $output_dir/collab_missing_index_files.txt
curl --user elastic:changeme -XGET "http://localhost:9200/pcawg-r1/file_object/_search?size=3000" -d '{
    "_source": ["file_object_id", "gnos_id", "dcc_project_code", "file_name", "donor_wgs_exclusion_white_gray", "analysis_software"],
    "query": {
        "bool": {
            "must" : [
              {
                "match" : { "is_in_pcawg_v1_4" : "true" }
                },
                {
                "match" : { "file_copies.repo_name" : "collab" }
                }
            ],
            "must_not":[ 
              {
                "match": {
                    "index_file_copies.repo_name": "collab"
                }
              },
              {
                "match" : { "file_format" : "Other" }
                }
              ]
    }
  }
}
' | jq -r '.hits.hits[]._source | [.dcc_project_code, .analysis_software, .gnos_id, .file_name, .file_object_id, .donor_wgs_exclusion_white_gray] | join("\t")' >> $output_dir/collab_missing_index_files.txt


# generate the list of index files missing from AWS
echo -e $header > $output_dir/aws_missing_index_files.txt
curl --user elastic:changeme -XGET "http://localhost:9200/pcawg-r1/file_object/_search?size=3000" -d '{
    "_source": ["file_object_id", "gnos_id", "dcc_project_code", "file_name", "donor_wgs_exclusion_white_gray", "analysis_software"],
    "query": {
        "bool": {
            "must" : [
              {
                "match" : { "is_in_pcawg_v1_4" : "true" }
                },
                {
                "match" : { "file_copies.repo_name" : "aws" }
                }
            ],
            "must_not":[ 
              {
                "match": {
                    "index_file_copies.repo_name": "aws"
                }
              },
              {
                "match" : { "file_format" : "Other" }
                }
              ]
    }
  },
    "sort" : [
        { "analysis_software.keyword" : {"order" : "desc"}},
        { "dcc_project_code.keyword" : {"order" : "asc"} },
        "_score"
    ]
}
' | jq -r '.hits.hits[]._source | [.dcc_project_code, .analysis_software, .gnos_id, .file_name, .file_object_id, .donor_wgs_exclusion_white_gray] | join("\t")' >> $output_dir/aws_missing_index_files.txt

# generate the list of index files missing from Collab existing in AWS
echo -e $header > $output_dir/index_files_missing_in_collab_existing_in_aws.txt
curl --user elastic:changeme -XGET "http://localhost:9200/pcawg-r1/file_object/_search?size=3000" -d '{
    "_source": ["file_object_id", "gnos_id", "dcc_project_code", "file_name", "donor_wgs_exclusion_white_gray", "analysis_software"],
    "query": {
        "bool": {
            "must" : [
              {
                "match" : { "is_in_pcawg_v1_4" : "true" }
                },
                {
                "match" : { "file_copies.repo_name" : "collab" }
                },
                {
                "match" : { "file_copies.repo_name" : "aws" }
                },
                {
                "match": { "index_file_copies.repo_name": "aws"}
                }
            ],
            "must_not":[ 
              {
                "match": {
                    "index_file_copies.repo_name": "collab"
                }
              },
              {
                "match" : { "file_format" : "Other" }
                }
              ]
    }
  },
    "sort" : [
        { "analysis_software.keyword" : {"order" : "desc"}},
        { "dcc_project_code.keyword" : {"order" : "asc"} },
        "_score"
    ]
}
' | jq -r '.hits.hits[]._source | [.dcc_project_code, .analysis_software, .gnos_id, .file_name, .file_object_id, .donor_wgs_exclusion_white_gray] | join("\t")' >> $output_dir/index_files_missing_in_collab_existing_in_aws.txt

# generate the list of files missing from DCC portal
echo -e $header > $output_dir/dcc_portal_missing_files.txt
curl --user elastic:changeme -XGET "http://localhost:9200/pcawg-r1/file_object/_search?size=3000" -d '{
    "_source": ["file_object_id", "gnos_id", "dcc_project_code", "file_name", "donor_wgs_exclusion_white_gray", "analysis_software"],
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
                "match" : { "file_copies.repo_name" : "dcc_portal" }
                }
              ]
    }
  },
    "sort" : [
        { "analysis_software.keyword" : {"order" : "desc"}},
        { "dcc_project_code.keyword" : {"order" : "asc"} },
        "_score"
    ]
}' | jq -r '.hits.hits[]._source | [.dcc_project_code, .analysis_software, .gnos_id, .file_name, .file_object_id, .donor_wgs_exclusion_white_gray] | join("\t")' >> $output_dir/dcc_portal_missing_files.txt



# generate the list of files_only_exist_in_one_repo
header="repo_name\tdcc_project_code\tanalysis_software\tgnos_id\tfile_name\tfile_object_id\tdonor_wgs_exclusion_white_gray"
echo -e $header > $output_dir/files_only_exist_in_one_repo.txt
curl --user elastic:changeme -XGET "http://localhost:9200/pcawg-r1/file_object/_search?size=21000" -d'
{
    "_source": ["file_object_id", "gnos_id", "dcc_project_code", "file_name", "donor_wgs_exclusion_white_gray", "analysis_software", "file_copies.repo_name"],
    "query": {
        "bool": {
            "minimum_should_match":"1",
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
            "should" : [
                { "bool": {
                   "must_not" : [
                    {
                     "match": {
                         "file_copies.repo_name": "dcc_portal"
                          }
                    },
                    {
                   "script" : {
                       "script" : {
                           "inline": "doc[\"file_copies.repo_name.keyword\"].values.length > 1", 
                      "lang": "painless"
                      }
                    }
                  }
                ]
              }
             },
                { "bool": {
                   "must" : [
                    {
                     "match": {
                         "file_copies.repo_name": "dcc_portal"
                          }
                    },
                    {
                   "script" : {
                       "script" : {
                           "inline": "doc[\"file_copies.repo_name.keyword\"].values.length < 3", 
                      "lang": "painless"
                      }
                    }
                  }
                ]
              }
             }
            ]
          }
    },
    "aggs" : {
        "analysis_softwares" : {
            "terms" : { "field" : "analysis_software.keyword" },
            "aggs" : {
                "repos" : { "terms" : { "field" : "file_copies.repo_name.keyword" } }
            }
        }
    },
    "sort" : [
        { "file_copies.repo_name.keyword" : {"order" : "desc"}},
        { "analysis_software.keyword" : {"order" : "desc"}},
        { "dcc_project_code.keyword" : {"order" : "asc"} },
        "_score"
    ]
}' | jq -r '.hits.hits[]._source | [.file_copies[].repo_name, .dcc_project_code, .analysis_software, .gnos_id, .file_name, .file_object_id, .donor_wgs_exclusion_white_gray] | . - ["dcc_portal"] | join("\t") ' >> $output_dir/files_only_exist_in_one_repo.txt



