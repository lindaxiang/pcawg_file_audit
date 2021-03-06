#!/usr/bin/env python

import os
import re
import yaml
import csv
import click
from elasticsearch import Elasticsearch
from collections import OrderedDict




def init_app(config_file, host=None, port=None, **kwargs):
    """
    Function to initialize workdir, by identifying config file and
    input source schema files and parse them.
    Returns application context dict.
    """
    app_ctx = {}

    app_ctx['app'] = yaml.load(config_file)

    workdir = os.path.abspath(app_ctx['app']['workdir'])
    confdir = os.path.abspath(app_ctx['app']['confdir'])

    app_ctx['input_dir'] = os.path.join(workdir, 'input')
    app_ctx['output_dir'] = os.path.join(workdir, 'output')

    try:
        with open(os.path.join(confdir, 'config.yaml'), 'r') as c:
            app_ctx['config'] = yaml.load(c)
    except:
        exit('Error: please make sure config.yaml exists and readable under the specified confdir: %s' % confdir)

    app_ctx['input_schemas'] = get_input_schemas(confdir)

    if (host and port):
        if host: app_ctx['config']['es.host'] = host
        if port: app_ctx['config']['es.port'] = port

        es_hosts = [ "%s:%s" % (app_ctx['config']['es.host'], app_ctx['config']['es.port']) ]
        app_ctx['es'] = Elasticsearch(hosts=es_hosts, http_auth=('elastic', 'changeme'), **kwargs)

    return app_ctx


def get_input_schemas(confdir):

    schemas = {}
    file_name_pattern = re.compile('^(.+)\.schema\.yaml$')
    for f in os.listdir(confdir):
        file_with_path = os.path.join(confdir, f)
        if not os.path.isfile(file_with_path): continue

        m = re.match(file_name_pattern, f)
        if m and m.group(1):
            if m.group(1) in schemas:
                click.echo('Schema for "%s" already defined, ignore: %s' % (m.group(1), file_with_path))
            else:
                with open(file_with_path, 'r') as s:
                    schemas[m.group(1)] = yaml.load(s)
                    # if schemas[m.group(1)]:
                        # schemas[m.group(1)]['data_path'] = os.join(workdir, m)

    return schemas


def read_annotations(annotations, type, file_name):
    if not os.path.isfile(file_name):
        return
    with open(file_name, 'r') as r:

        if type == 'pcawg_donorlist':
            annotations[type] = set()
            reader = csv.DictReader(r, delimiter='\t')
            for row in reader:
                annotations[type].add(row.get('donor_unique_id'))

        elif type in ['blacklist', 'graylist', 'has_mirna_data']:
            annotations[type] = set()
            for line in r:
                if line.startswith('#'): continue
                if len(line.rstrip()) == 0: continue
                annotations[type].add(line.rstrip())

        elif type == 'uuid_to_barcode':
            annotations[type] = {}
            for line in r:
                if line.startswith('#'): continue
                if len(line.rstrip()) == 0: continue
                TCGA_project, subtype, uuid, barcode = str.split(line.rstrip(), '\t')
                uuid = detect_and_low_case_uuid(uuid)
                annotations[type][uuid] = barcode 

        elif type == 'specimen_type_to_cv':
            annotations[type] = {}
            for line in r:
                if line.startswith('#'): continue
                if len(line.rstrip()) == 0: continue
                tcga_specimen_type, icgc_cv_term = str.split(line.rstrip(), '\t')
                annotations[type][tcga_specimen_type] = icgc_cv_term 


        elif type == 'specimen_uuid_to_type':
            annotations[type] = {}
            for line in r:
                if line.startswith('#'): continue
                if len(line.rstrip()) == 0: continue
                donor_id, specimen_barcode, specimen_type, specimen_uuid = str.split(line.rstrip(), '\t')
                annotations[type][specimen_uuid] = specimen_type 


        elif type in ['icgc_donor_id', 'icgc_sample_id', 'icgc_specimen_id']:
            annotations[type] = {}
            subtype = type.split('_')[1]
            prefix = subtype[0:2]
            for line in r:
                if line.startswith('#'): continue
                if len(line.rstrip()) == 0: continue
                icgc_id, id_pcawg, dcc_project_code, creation_release = str.split(line.rstrip(), ',')
                id_pcawg = detect_and_low_case_uuid(id_pcawg)
                annotations[type][dcc_project_code+'::'+id_pcawg] = prefix.upper()+icgc_id
        
        elif type == 'object_id_map':
            annotations[type] = {}
            for line in r:
                if line.startswith('#'): continue
                if len(line.rstrip()) == 0: continue
                if not len(str.split(line.rstrip(), '\t')) == 3: continue
                object_id, gnos_id, file_name = str.split(line.rstrip(), '\t')
                annotations[type][gnos_id+'.'+file_name] = object_id
                annotations[type][object_id] = {'gnos_id': gnos_id, 'file_name': file_name}             

        else:
            print('unknown annotation type: {}'.format(type))
    return annotations

def detect_and_low_case_uuid(submitter_id):
    uuid_pattern = re.compile('^[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}\Z', re.I)
    uuid = submitter_id.lower() if uuid_pattern.search(submitter_id) else submitter_id
    return uuid

def get_icgc_id(donor_unique_id, submitter_id, subtype, annotations):
    submitter_id = detect_and_low_case_uuid(submitter_id)
    dcc_project_code, submitter_donor_id = donor_unique_id.split('::')
    if dcc_project_code.endswith('-US'):
        if not annotations.get('uuid_to_barcode').get(submitter_id):
            return 'missing'
        submitter_id = annotations.get('uuid_to_barcode').get(submitter_id)

    if not annotations.get('icgc_'+subtype+'_id').get(dcc_project_code+'::'+submitter_id):
        # write to the file for those donor/specimen/sample missing icgc ids
        # disable it for now since all ids have icgc ids
        # with open('missing_icgc_id.txt', 'a') as f:
        #     f.write('\t'.join([dcc_project_code,subtype,submitter_id])+'\n')
        return 'missing'
    icgc_id = annotations.get('icgc_'+subtype+'_id').get(dcc_project_code+'::'+submitter_id)
    return icgc_id

def get_line(obj):
    line = []
    for k, v in obj.iteritems():
        if isinstance(v, list):
            field = []
            for q in v:
                if isinstance(q, list):
                    field.append('|'.join(q))
                elif q is None:
                    field.append('')
                else:
                    field.append(str(q))
            line.append(','.join(field))

        elif v is None:
            line.append('')
        else:
            line.append(str(v))
    return line


def get_dict_value(fields, json_obj, field_map):
    tsv_obj = OrderedDict()
    for f in fields:
        fm = field_map.get(f)
        if not fm: continue
        value = reduce(udf, fm.split('.'), json_obj)
        tsv_obj[f] = value
    return tsv_obj    

def udf(x, y):
    if not x:
        return
    if isinstance(x, dict):
        value = x.get(y)
    elif isinstance(x, list):
        value = [udf(a,y) for a in x]
    return value

def get_key_map(key):
    key_map = {
      "sanger": "sanger_variant_calling",
      "dkfz": "dkfz_embl_variant_calling",
      "embl": "dkfz_embl_variant_calling",
      "broad": "broad_variant_calling",
      "muse": "muse_variant_calling",
      "broad_tar": "broad_tar_variant_calling",
      "aligned_bam": "bwa_alignment",
      "minibam": "minibam",
      "https://gtrepo-bsc.annailabs.com/": "gnos_bsc",
      "bsc": "https://gtrepo-bsc.annailabs.com/",
      "https://gtrepo-ebi.annailabs.com/": "gnos_ebi",
      "ebi": "https://gtrepo-ebi.annailabs.com/",
      "https://cghub.ucsc.edu/": "gnos_cghub",
      "cghub": "https://cghub.ucsc.edu/",
      "https://gtrepo-dkfz.annailabs.com/": "gnos_dkfz",
      "dkfz": "https://gtrepo-dkfz.annailabs.com/",
      "https://gtrepo-riken.annailabs.com/": "gnos_riken",
      "riken": "https://gtrepo-riken.annailabs.com/",
      "https://gtrepo-osdc-icgc.annailabs.com/": "gnos_osdc-icgc",
      "osdc-icgc": "https://gtrepo-osdc-icgc.annailabs.com/",
      "https://gtrepo-osdc-tcga.annailabs.com/": "gnos_osdc-tcga",
      "osdc-tcga": "https://gtrepo-osdc-tcga.annailabs.com/",
      "https://gtrepo-etri.annailabs.com/": "gnos_etri",
      "etri": "https://gtrepo-etri.annailabs.com/",
      "collab": "collab",
      "aws": "aws",
      "dcc_portal": "dcc_portal",
      "ega": "ega",
      "pdc": "pdc"
    }   

    return key_map.get(key)




