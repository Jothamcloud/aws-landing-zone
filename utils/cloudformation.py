import boto3
from botocore.exceptions import ClientError

class CloudFormationHelper:
    """Helper class to manage CloudFormation stack operations"""
    
    def __init__(self, region: str, role_arn: str = None):
        """Initialize with region and optional role ARN to assume"""
        session = boto3.Session(region_name=region)
        
        if role_arn:
            sts = session.client('sts')
            credentials = sts.assume_role(
                RoleArn=role_arn,
                RoleSessionName='landing-zone-deployment'
            )['Credentials']
            
            self.cfn = boto3.client(
                'cloudformation',
                region_name=region,
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken']
            )
        else:
            self.cfn = session.client('cloudformation')

    def deploy_stack(self, stack_name: str, template_body: str) -> dict:
        """
        Deploy or update a CloudFormation stack
        
        Args:
            stack_name: Name of the stack
            template_body: CloudFormation template content
            
        Returns:
            dict: Stack operation response
        """
        try:
            try:
                response = self.cfn.update_stack(
                    StackName=stack_name,
                    TemplateBody=template_body,
                    Capabilities=['CAPABILITY_NAMED_IAM']
                )
            except ClientError as e:
                if 'No updates are to be performed' in str(e):
                    return {'StackId': stack_name, 'Status': 'NO_UPDATES_NEEDED'}
                raise e
        except ClientError as e:
            if 'does not exist' in str(e):
                response = self.cfn.create_stack(
                    StackName=stack_name,
                    TemplateBody=template_body,
                    Capabilities=['CAPABILITY_NAMED_IAM']
                )
            else:
                raise e
                
        return response
