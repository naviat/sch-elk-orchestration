#!/usr/bin/python

import time
import boto.opsworks
import argparse
import os

# Arguments
parser = argparse.ArgumentParser()
parser.add_argument('-r', '--region',
                    default='us-west-2',
                    type=str, help='AWS region')
parser.add_argument('-o', '--opsworks_region',
                    default='us-east-1',
                    type=str, help='Opsworks region endpoint')
parser.add_argument('-s', '--shipper_opsworks_layer_id',
                    default='6b51b650-bc78-4bbc-8d0c-67e3b8db22ac',
                    type=str, help='Opsworks ID of the Shipper Layer')
parser.add_argument('-cd', '--cooldown_period',
                    default=5,
                    type=int, help='Cooldown period in minutes before ' +
                    'scale down of shipper')
parser.add_argument('-en', '--elk_pipeline_metric_namespace',
                    default='Logstash',
                    type=str,
                    help='Custom Cloudwatch metric namespace used for ' +
                         'ELK Pipeline')
parser.add_argument('-em', '--elk_pipeline_metric_name',
                    default='ELK_Pipeline_Status',
                    help='Custom Cloudwatch metric name used for ' +
                    'ELK Pipeline')
args = parser.parse_args()
region = args.region
opsworks_region = args.opsworks_region
shipper_opsworks_layer_id = args.shipper_opsworks_layer_id
cooldown_period_minutes = args.cooldown_period
elk_pipeline_metric_name = args.elk_pipeline_metric_name
elk_pipeline_metric_namespace = args.elk_pipeline_metric_namespace

print 'Start time: ' + time.ctime()
# Trigger population custom Cloudwatch metric for the pipeline
os.system("echo '* * * * * /usr/bin/aws cloudwatch put-metric-data " +
          "--metric-name " +
          elk_pipeline_metric_name + " --namespace " +
          elk_pipeline_metric_namespace +
          " --value 1 --region " + region + "' | crontab -")

try:
    # Wait for cooldown period for drain its buffer
    for i in range(0, cooldown_period_minutes):
        print('{0}:Waiting for cooldown period before scaling down. {1} ' +
              'minutes left ').format(time.ctime(),
                                      str(cooldown_period_minutes-i))
        time.sleep(60)

    # Get Status of the Opswork instances in Shipper layer
    opswork = boto.opsworks.connect_to_region(opsworks_region)
    instances_to_stop = []

    print 'Checking status of Opsworks instances in Shipper Layer'
    instances = opswork.describe_instances(layer_id=shipper_opsworks_layer_id)
    for key, value in instances.items():
        for i in range(0, len(value)):
            shipper_status = value[i].get('Status')
            shipper_opswork_id = value[i].get('InstanceId')

        if shipper_status != 'online':
            raise Exception('Shipper instance with opsworks id ' +
                            shipper_opswork_id +
                            ' expected status is online. It is currently ' +
                            shipper_status +
                            '. Another process could already be working.')

        instances_to_stop.append(shipper_opswork_id)

    # Stop Shipper instance
    for instance in instances_to_stop:
        print 'Stopping Shipper instance with opsworks id ' + instance
        opswork.stop_instance(instance)
except:
    # Flag end of pipeline execution
    os.system("echo '' | crontab -")
    os.system("/usr/bin/aws cloudwatch put-metric-data --metric-name " +
              elk_pipeline_metric_name + " --namespace " +
              elk_pipeline_metric_namespace + " --value=0 --region " + region)
    raise
