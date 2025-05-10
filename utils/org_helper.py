import boto3
from botocore.exceptions import ClientError
from typing import Optional, Dict, List

class OrganizationHelper:
    """Helper class to manage AWS Organizations operations"""
    
    def __init__(self, region: str):
        """Initialize with region"""
        self.org_client = boto3.client('organizations', region_name=region)
        self.sts = boto3.client('sts', region_name=region)
        
    def create_organizational_unit(self, name: str, parent_id: str) -> dict:
        """
        Create an organizational unit
        
        Args:
            name: Name of the OU
            parent_id: ID of parent OU or root
            
        Returns:
            dict: Created OU details
        """
        try:
            response = self.org_client.create_organizational_unit(
                ParentId=parent_id,
                Name=name
            )
            return response['OrganizationalUnit']
        except ClientError as e:
            raise e

    def create_account(self, name: str, email: str, ou_id: Optional[str] = None) -> dict:
        """
        Create a new AWS account
        
        Args:
            name: Account name
            email: Root email for account
            ou_id: Optional OU to place account in
            
        Returns:
            dict: Created account details
        """
        try:
            response = self.org_client.create_account(
                AccountName=name,
                Email=email
            )
            
            if ou_id:
                account_id = response['CreateAccountStatus']['AccountId']
                self.org_client.move_account(
                    AccountId=account_id,
                    SourceParentId=self._get_root_id(),
                    DestinationParentId=ou_id
                )
                
            return response['CreateAccountStatus']
        except ClientError as e:
            raise e

    def attach_policy(self, policy_id: str, target_id: str) -> dict:
        """
        Attach an SCP to an OU or account
        
        Args:
            policy_id: ID of the service control policy
            target_id: ID of the target OU or account
            
        Returns:
            dict: Response from attach operation
        """
        try:
            response = self.org_client.attach_policy(
                PolicyId=policy_id,
                TargetId=target_id
            )
            return response
        except ClientError as e:
            raise e

    def list_accounts(self) -> List[Dict]:
        """
        List all accounts in organization
        
        Returns:
            List[Dict]: List of account details
        """
        try:
            response = self.org_client.list_accounts()
            return response['Accounts']
        except ClientError as e:
            raise e

    def _get_root_id(self) -> str:
        """Get the organization root ID"""
        try:
            response = self.org_client.list_roots()
            return response['Roots'][0]['Id']
        except ClientError as e:
            raise e
