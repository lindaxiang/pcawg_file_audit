# pcawg_file_audit
The tool is used to:
* Audit PCAWG files distributed among different repos: Collab, AWS, EGA, DCC-portal, PDC, GNOS repositories

## Getting Started
The tool needs to talk to the Collaboratory, AWS S3, DCC portal API, metadata service API and EGA data transfer git repo to get latest information. 

### Prerequisites
Before you can run the tool:
* Have an Elaticsearch service running
* Have the PCAWG release May2016 JSONL dump file available at: `examples/file_auditing/input/`
* Configure the tool. The configuration file locates `config/fileobject.schema.yaml`. You may need to change the following field to indicate the path of EGA git repo on your local machine.
```
pcawg_ega_submission_path: /Users/lxiang/projects/pancan/pancancer-sandbox/pcawg-ega-submission
```
### Installing
Get the source script of the tool
```
git clone https://github.com/lindaxiang/pcawg_file_audit.git
```

### Running the tool
```
cd bin/
./pcawg_file_audit.sh
```

### The location of the output reports
```
examples/file_auditing/output/
├── aws_missing_files.txt
├── aws_missing_index_files.txt
├── collab_missing_files.txt
├── collab_missing_index_files.txt
├── dcc_portal_missing_files.txt
├── fileobject.jsonl
├── files_only_exist_in_one_repo.txt
├── index_files_missing_in_collab_existing_in_aws.txt
└── overall_report.txt
```
