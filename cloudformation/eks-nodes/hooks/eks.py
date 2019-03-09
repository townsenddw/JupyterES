#!/bin/python3

import subprocess
import boto3
import jinja2
import os

iam = boto3.client('iam')

def aws(*args, **kwargs):
    #logging.info("Executing kubectl", ' '.join(args))
    return subprocess.check_call(['aws'] + list(args), **kwargs)

def kubectl(*args, **kwargs):
    #logging.info("Executing kubectl", ' '.join(args))
    return subprocess.check_call(['kubectl'] + list(args), **kwargs)

def helm(*args, **kwargs):
    # logging.info("Executing helm", ' '.join(args))
    return subprocess.check_call(['helm'] + list(args), **kwargs)

def writeAuthCM(nodeArn, ADMINS):
    ## Apply ARN of instance role of worker nodes and apply to cluster
    print(os.getcwd())
    templateLoader = jinja2.FileSystemLoader(searchpath="./hooks")
    templateEnv = jinja2.Environment(loader=templateLoader)
    TEMPLATE_FILE = "aws-auth-cm.yaml.template"
    template = templateEnv.get_template(TEMPLATE_FILE)
    outputText = template.render(arn=nodeArn, users=ADMINS)
    with open('aws-auth-cm.yaml', 'w') as ofile:
        ofile.writelines(outputText)

def installConfigMap(provider, context, clusterName, nodeArn):
    ## Generate aws-auth-cm.yaml and apply to cluster
    print(nodeArn)
    print(os.getcwd())
    ADMINS = iam.get_group(GroupName='admin')['Users']
    writeAuthCM(nodeArn, ADMINS)
    aws('eks','update-kubeconfig', '--name', clusterName)
    return kubectl('apply', '-f', 'aws-auth-cm.yaml')

def installStorageClass(provider, context):
    ## Storage Class
    try:
        kubectl('delete', 'storageclass', 'gp2')
    except:
        pass
    finally:
        kubectl('apply', '-f', 'storageclass.yaml')

def installHelm(provider, context):
    ## Install Tiller serviceaccount and clusterrolbinding - Idempotent
    # Tiller ServiceAccount Creation
    try:
        kubectl('-n','kube-system','get','serviceaccount','tiller')
    except:
        kubectl('--namespace', 'kube-system', 'create', 'serviceaccount', 'tiller')

    # ClusterRoleBinding
    try:
        kubectl('get', 'clusterrolebinding', 'tiller')
    except:
        kubectl('create', 'clusterrolebinding', 'tiller', '--clusterrole=cluster-admin', '--serviceaccount=kube-system:tiller')

    # Inititalize Helm/Tiller for the cluster
    helm('init', '--service-account', 'tiller')