#!/bin/bash

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

cd $DIR

input_dir='../examples/file_auditing/input'

MAX_NUM1=31
MAX_NUM2=170
MAX_NUM3=704

# get the latest information for ega
echo update pcawg-ega-submission git repository
EGA_PATH=$(grep 'pcawg_ega_submission_path:' ../config/file_auditing/fileobject.schema.yaml); EGA_PATH=${EGA_PATH//*pcawg_ega_submission_path: /};
cd $EGA_PATH
git checkout master
git pull
cd $DIR

# get the latest object_ids on Collab
echo "#updated at: $(date)" > $input_dir/collab.object_id.txt
aws --endpoint-url https://object.cancercollaboratory.org:9080 s3 ls s3://oicr.icgc/data/ | awk '{print $4}' | grep -v "^$" >> $input_dir/collab.object_id.txt
for i in $(eval echo "{0..$MAX_NUM1}")
do 
    aws --endpoint-url https://object.cancercollaboratory.org:9080 s3 ls s3://oicr.icgc.$i/data/ | awk '{print $4}' >> $input_dir/collab.object_id.txt
done

# get the latest object_ids on AWS
echo "#updated at: $(date)" > $input_dir/aws.object_id.txt
aws --profile amazon_pay s3 ls s3://oicr.icgc/data/ | awk '{print $4}' | grep -v "^$" |grep -v meta |grep -v heliograph >> $input_dir/aws.object_id.txt

# get the latest object list on dcc portal
rm -f $input_dir/dcc.object_id.txt 
touch $input_dir/dcc.object_id.txt
echo "get all the PCAWG data file object_ids on DCC portal"
for i in $(eval echo "{0..$MAX_NUM3}")
do 
    curl -XGET "https://dcc.icgc.org/api/v1/repository/files?filters=%7B%22file%22:%7B%22study%22:%7B%22is%22:%5B%22PCAWG%22%5D%7D%7D%7D&size=100&from=$(($i * 100 + 1))" |jq -r '.hits[] | .objectId, (.fileCopies[]?.indexFile.objectId)' |sort|uniq |grep -v null  >> $input_dir/dcc.object_id.txt
done


# get the latest object_id, gnos_id, and file_name mapping from metadata service API
rm -f $input_dir/dcc.object_id_map.part1.txt 
touch $input_dir/dcc.object_id_map.part1.txt
echo "get all the PCAWG object_ids mapping from meta id service API"
for i in $(eval echo "{0..$MAX_NUM2}")
do 
    curl -XGET "https://meta.icgc.org/entities?size=2000&page=${i}"|jq -r '.content[] | [.id, .gnosId, .fileName] | join("\t")' >> $input_dir/dcc.object_id_map.part1.txt 
done

# get all the PCAWG object_ids mapping from DCC portal API
rm -f $input_dir/dcc.object_id_map.part2.txt
touch $input_dir/dcc.object_id_map.part2.txt
echo "get all the PCAWG object_ids mapping from DCC portal API"
echo "get the data file objects"
for i in $(eval echo "{0..$MAX_NUM3}")
do 
    curl -XGET "https://dcc.icgc.org/api/v1/repository/files?filters=%7B%22file%22:%7B%22study%22:%7B%22is%22:%5B%22PCAWG%22%5D%7D%7D%7D&size=100&from=$(($i * 100 + 1))" |jq -r '.hits[]| .objectId as $objectId | (.fileCopies[]?|[$objectId, .repoDataBundleId, .fileName]) |join("\t")' | sort | uniq  >> $input_dir/dcc.object_id_map.part2.txt
done

echo "get the index file objects"
for i in $(eval echo "{0..$MAX_NUM3}")
do 
    curl -XGET "https://dcc.icgc.org/api/v1/repository/files?filters=%7B%22file%22:%7B%22study%22:%7B%22is%22:%5B%22PCAWG%22%5D%7D%7D%7D&size=100&from=$(($i * 100 + 1))" |jq -r '.hits[].fileCopies[]| .repoDataBundleId as $repoDataBundleId | (.indexFile|[.objectId, $repoDataBundleId, .fileName]) |join("\t")' | sort | uniq  >> $input_dir/dcc.object_id_map.part2.txt
done

echo "remove the duplicates"
echo "#updated at: $(date)" > $input_dir/dcc.object_id_map.txt
cat $input_dir/dcc.object_id_map.part*.txt | grep -v EGA | sort | uniq >> $input_dir/dcc.object_id_map.txt





