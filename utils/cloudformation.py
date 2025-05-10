import boto3
import time
from botocore.exceptions import ClientError, WaiterError
from .logger import setup_logging

logger = setup_logging()

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
        Deploy or update a CloudFormation stack and wait for completion
        
        Args:
            stack_name: Name of the stack
            template_body: CloudFormation template content
            
        Returns:
            dict: Stack operation response
        """
        try:
            try:
                logger.info(f"Attempting to update stack: {stack_name}")
                response = self.cfn.update_stack(
                    StackName=stack_name,
                    TemplateBody=template_body,
                    Capabilities=['CAPABILITY_NAMED_IAM']
                )
                operation = 'UPDATE'
            except ClientError as e:
                if 'No updates are to be performed' in str(e):
                    logger.info(f"No updates needed for stack: {stack_name}")
                    return {'StackId': stack_name, 'Status': 'NO_UPDATES_NEEDED'}
                elif 'does not exist' in str(e):
                    logger.info(f"Creating new stack: {stack_name}")
                    response = self.cfn.create_stack(
                        StackName=stack_name,
                        TemplateBody=template_body,
                        Capabilities=['CAPABILITY_NAMED_IAM']
                    )
                    operation = 'CREATE'
                else:
                    logger.error(f"Failed to deploy stack: {str(e)}")
                    raise

            stack_id = response['StackId']
            self._wait_for_stack_operation(stack_id, operation)
            return self._get_stack_status(stack_id)

        except ClientError as e:
            logger.error(f"Failed to deploy stack: {str(e)}")
            raise

    def _wait_for_stack_operation(self, stack_id: str, operation: str):
        """Wait for stack operation to complete"""
        try:
            waiter = self.cfn.get_waiter(f'stack_{operation.lower()}_complete')
            logger.info(f"Waiting for stack {operation} to complete...")
            waiter.wait(
                StackName=stack_id,
                WaiterConfig={'Delay': 30, 'MaxAttempts': 30}
            )
            logger.info(f"Stack {operation} completed successfully")
        except WaiterError as e:
            logger.error(f"Stack {operation} failed: {str(e)}")
            raise

    def _get_stack_status(self, stack_id: str) -> dict:
        """Get detailed stack status"""
        response = self.cfn.describe_stacks(StackName=stack_id)
        return response['Stacks'][0]
