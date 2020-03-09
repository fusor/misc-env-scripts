#cat noobaa_buckets.txt | cut -d' ' -f3- | xargs -n1 -t aws s3api list-objects --bucket
#cat noobaa_buckets.txt | cut -d' ' -f3- | xargs -n1 -t aws s3api delete-objects --bucket
cat noobaa_buckets.txt | cut -d' ' -f3- | xargs -n1 -t -I {} aws s3 rm s3://{} --recursive
#cat noobaa_buckets.txt | cut -d' ' -f3- | xargs -n1 -t aws s3api delete-bucket --bucket

#aws s3 rm s3://noobaa-backing-store-db8bf0a0-ca42-4e64-a3c4-6d9398c0529a --recursive


