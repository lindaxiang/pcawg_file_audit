import os
import sys
import click
import util
from elasticsearch import Elasticsearch
import json
import copy
import uuid
import glob

 
def build_fileobject(app_ctx):

    click.echo('In build_fileobject...')
    schema = app_ctx['input_schemas']['fileobject']

    fname = os.path.join(app_ctx['input_dir'], schema['pcawg_release_file_name'])
    fout_name = os.path.join(app_ctx['output_dir'], schema['output_file_name'])

    annotations = {}
    util.read_annotations(annotations, 'object_id_map', app_ctx['input_dir']+'/dcc.object_id_map.txt')
    

    file_object = {}
    file_object_map = {}
    # build file objects from PCAWG release dump
    with open(fname, 'r') as f:
        for l in f:
            es_json = json.loads(l)
            create_file_object(es_json, annotations, schema, file_object, file_object_map)
    
    # add information from collab and aws objects
    for source in ['collab', 'aws', 'pdc', 'dcc_portal']:
        fname = os.path.join(app_ctx['input_dir'], schema[source+'_object_list'])
        add_info_to_file_object(file_object, file_object_map, fname, source, annotations, schema)

    # add information from ega
    fname = os.path.join(schema['pcawg_ega_submission_path'], '*', 'analysis_*.PCAWG_*', 'EGAD*.files.tsv')
    print fname
    files = glob.glob(fname)
    print files
    for f in files:
        print f
        add_info_to_file_object(file_object, file_object_map, f, 'ega', annotations, schema)


    # push to ES
    click.echo('Push to Elasticsearch...')
    es_index_name = app_ctx['config']['es.index_name']
    if app_ctx.get('es') and app_ctx['es'].indices.exists(index=es_index_name):
        app_ctx['es'].indices.delete(index=es_index_name, timeout='10s')
        for key, value in file_object.iteritems():
            app_ctx['es'].index(index=es_index_name, doc_type="file_object", id=key, body=value) 

    click.echo('Write to the JSONL dump...')
    with open(fout_name, 'w') as f:
        for key, value in file_object.iteritems():
            f.write(json.dumps(value)+'\n') 
    


def create_file_object(es_json, annotations, schema, file_object, file_object_map):
    file_dict = copy.deepcopy(schema['target_schema']['fileobject'])

    file_dict['is_in_pcawg_v1_4'] = True
    for k, v in schema['root_fields_map'].iteritems():
        if not k in file_dict.keys(): continue
        file_dict[k] = es_json.get(v)

    for fields in schema['fields_path_map']:
        for key, value in fields.iteritems():
            # update the data_type, file_type and analysis_software
            for k, v in value.iteritems(): 
                file_dict[k]=v  
            # find the files and populate the file, index_file and meta_file
            analysis = reduce(util.udf, key.split('.'), es_json)
            if isinstance(analysis, list):
                for a in analysis:
                    build_object(a, file_dict, file_object, schema, annotations, file_object_map)
            elif isinstance(analysis, dict):
                build_object(analysis, file_dict, file_object, schema, annotations, file_object_map)
            else:
                pass

    
    return file_object


def build_object(analysis, file_dict, file_object, schema, annotations, file_object_map):

    file_dict['gnos_id'] = analysis.get('gnos_id', None)
    
    file_names = []
    file_object_ids = []
    for f in analysis['files']:
        file_name = f['file_name']
        if file_name in file_names: continue
        if file_name.split('.')[-1] in ['bai', 'tbi', 'idx']: continue
        if f['file_size'] == 0: continue

        if file_name.endswith('bam'):
            file_dict['file_format'] = 'BAM'                      

        elif file_name.endswith('vcf.gz'):
            file_dict['file_format'] = 'VCF'
            file_dict['data_type'] = 'Unknown'
            for fields in schema['vcf_fields_type_map']:
                for key, value in fields.iteritems():
                    if not file_name.endswith(key): continue
                    for k, v in value.iteritems():
                        file_dict[k] = v

        else:
            file_dict['file_format'] = "Other"
            file_dict['data_type'] = "Unknown"

        #clear the content
        for k in ['', 'index_', 'meta_']:
            for p in ['file_name', 'file_object_id', 'file_copies']:
                file_dict[k+p] = None

        file_dict = create_file(analysis, f, file_dict, file_name, file_names, annotations)
        if file_dict.get('file_object_id'): 
            key = file_dict['file_object_id']
        else: # random generate one key
            key = '_%s' % str(uuid.uuid4()).replace('-','')

        for k in ['file_object_id', 'index_file_object_id', 'meta_file_object_id']:
            if not file_dict.get(k): continue
            if not file_object_map.get(file_dict[k]): file_object_map[file_dict[k]] = []
            file_object_map[file_dict[k]].append(copy.deepcopy(key))

        file_object[key] = copy.deepcopy(file_dict)

    return file_object

def create_file(analysis, file_info, file_dict, file_name, file_names, annotations):
    # data
    file_dict['file_name'] = file_name
    file_dict['file_object_id'] = annotations['object_id_map'].get(file_dict['gnos_id']+'.'+file_name, None)
    file_names.append(file_name)
    file_dict['file_copies'] = create_file_copies(analysis, file_info)
    # index
    for g in analysis['files']:
        if not g['file_name'] in [file_name+a for a in ['.bai', '.tbi', '.idx']]: continue
        file_dict['index_file_name'] = g['file_name']
        file_dict['index_file_object_id'] = annotations['object_id_map'].get(file_dict['gnos_id']+'.'+g['file_name'], None)
        file_names.append(file_name)
        file_dict['index_file_copies'] = create_file_copies(analysis, g) 
    # meta
    file_dict['meta_file_name'] = analysis['gnos_id'] + '.xml'
    file_dict['meta_file_object_id'] = annotations['object_id_map'].get(file_dict['gnos_id']+'.'+file_dict['meta_file_name'], None)
    file_dict['meta_file_copies'] = [util.get_key_map(r) for r in analysis['gnos_repo']]

    return file_dict

def create_file_copies(analysis, file_info):
    file_copies = []
    for r in analysis['gnos_repo']:
        file_copy = {}
        file_copy['repo_name'] = util.get_key_map(r)
        file_copy['file_size'] = file_info['file_size']
        file_copy['file_md5sum'] = file_info['file_md5sum']
        file_copies.append(file_copy)

    return file_copies

def add_info_to_file_object(file_object, file_object_map, fname, source, annotations, schema):
    with open(fname, 'r') as f:
        for line in f:
            if line.startswith('#'): continue
            if len(line.rstrip()) == 0: continue

            if source in ['collab', 'aws', 'pdc', 'dcc_portal']:
                object_id = line.rstrip()
                file_info = {
                    "repo_name": util.get_key_map(source)
                }
                gnos_id = None
                if annotations['object_id_map'].get(object_id):
                    gnos_id = annotations['object_id_map'].get(object_id).get('gnos_id')
                    file_info = {
                       "file_name": annotations['object_id_map'].get(object_id).get('file_name'),
                       "repo_name": util.get_key_map(source)
                    } 

            elif source in ['ega']:
                if line.startswith('dataset_id'): continue
                gnos_id, file_name = str.split(line.rstrip(), '\t')[-1].split('/')
                file_info = {
                   "file_name": file_name,
                   "repo_name": util.get_key_map(source)
                }                
                object_id = annotations['object_id_map'].get(gnos_id+'.'+file_name, '_%s' % str(uuid.uuid4()).replace('-',''))
            
            else:
                return

            if object_id:
                if file_object_map.get(object_id):
                    append_file_copies(file_object, file_object_map, object_id, file_info)
                else:
                    create_unrecognized_file_object(file_object, object_id, annotations, schema, file_info, gnos_id)

    return file_object

def append_file_copies(file_object, file_object_map, object_id, file_copy):
    
    for f_id in file_object_map[object_id]:
        object_content = file_object[f_id]
        if object_content['file_object_id'] == object_id:
            object_content['file_copies'].append(file_copy)
        elif object_content['index_file_object_id'] == object_id:
            object_content['index_file_copies'].append(file_copy)
        elif object_content['meta_file_object_id'] == object_id:
            object_content['meta_file_copies'].append(file_copy['repo_name'])
        else:
            pass 

    return file_object

def create_unrecognized_file_object(file_object, object_id, annotations, schema, file_info, gnos_id=None):
    file_dict = copy.deepcopy(schema['target_schema']['fileobject'])
    file_dict['is_in_pcawg_v1_4'] = False

    file_dict['file_object_id'] = object_id
    if annotations['object_id_map'].get(object_id):
        file_dict['file_name'] = annotations['object_id_map'].get(object_id).get('file_name')
        file_dict['gnos_id'] = annotations['object_id_map'].get(object_id).get('gnos_id')
    else:
        file_dict['file_name'] = file_info.get('file_name')
        file_dict['gnos_id'] = gnos_id

    file_dict['file_copies'].append(file_info)

    file_object[object_id] = copy.deepcopy(file_dict)

    return file_object




    
