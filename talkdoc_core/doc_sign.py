import base64
import os
from typing import Optional

from docusign_esign import (
    ApiClient,
    Document,
    EnvelopeDefinition,
    EnvelopesApi,
    RecipientViewRequest,
    Signer,
    SignHere,
    Tabs,
)
from dotenv import load_dotenv

load_dotenv(".env")


class DocuSignClient:
    """Handles DocuSign authentication and envelope operations."""

    def __init__(self):
        self.integrator_key = os.getenv('DS_CLIENT_ID')
        self.user_id = os.getenv('DS_IMPERSONATED_USER_GUID')
        self.account_id = os.getenv('DS_ACCOUNT_ID')
        self.private_key_path = os.getenv('DS_PRIVATE_KEY_PATH')
        self.demo_server = os.getenv('DS_DEMO_SERVER')
        self.auth_server = os.getenv('DS_AUTH_SERVER')
        self.app_url = os.getenv('APP_URL')
        self.api_client: Optional[ApiClient] = None
        self.access_token: Optional[str] = None
        self.account_id: Optional[str] = self.account_id
        self.envelopes_api: Optional[EnvelopesApi] = None

    def authenticate(self) -> bool:
        """Authenticate with DocuSign using JWT and set up the API client."""
        try:
            self.api_client = ApiClient()
            self.api_client.host = f"{self.demo_server}/restapi"
            with open(self.private_key_path, 'r') as key_file:
                private_key = key_file.read()
            jwt_token = self.api_client.request_jwt_user_token(
                client_id=self.integrator_key,
                user_id=self.user_id,
                oauth_host_name=self.auth_server,
                private_key_bytes=private_key.encode('ascii'),
                expires_in=3600
            )
            self.access_token = jwt_token.access_token
            self.api_client.set_default_header(
                header_name="Authorization",
                header_value=f"Bearer {self.access_token}"
            )
            user_info = self.api_client.get_user_info(self.access_token)
            accounts = user_info.get_accounts()
            if accounts:
                if not self.account_id:
                    self.account_id = accounts[0].account_id
                self.envelopes_api = EnvelopesApi(self.api_client)
                return True
            else:
                print("No accounts found for user.")
                return False
        except Exception as e:
            print(f"DocuSign authentication failed: {e}")
            return False

    def create_envelope(
        self,
        pdf_path: str,
        signer_email: str,
        signer_name: str,
        client_user_id: str = "1234"
    ) -> Optional[str]:
        """Create an envelope for embedded signing and return the envelope ID."""
        try:
            with open(pdf_path, "rb") as file:
                document_b64 = base64.b64encode(file.read()).decode("ascii")
            envelope_definition = EnvelopeDefinition(
                email_subject="Please sign this document",
                documents=[Document(
                    document_base64=document_b64,
                    name="Document",
                    file_extension="pdf",
                    document_id="1"
                )],
                recipients={"signers": [Signer(
                    email=signer_email,
                    name=signer_name,
                    recipient_id="1",
                    client_user_id=client_user_id,
                    tabs=Tabs(sign_here_tabs=[SignHere(
                        anchor_string="/sn1/",
                        anchor_units="pixels",
                        anchor_x_offset="20",
                        anchor_y_offset="10"
                    )])
                )]},
                status="sent"
            )
            result = self.envelopes_api.create_envelope(
                self.account_id, envelope_definition=envelope_definition
            )
            return result.envelope_id
        except Exception as e:
            print(f"Error creating envelope: {e}")
            return None

    def create_recipient_view(
        self,
        envelope_id: str,
        signer_email: str,
        signer_name: str,
        client_user_id: str = "1234"
    ) -> Optional[str]:
        """Create a recipient view (embedded signing URL) for the envelope."""
        try:
            view_request = RecipientViewRequest(
                return_url=self.app_url,
                client_user_id=client_user_id,
                authentication_method="None",
                user_name=signer_name,
                email=signer_email
            )
            recipient_view = self.envelopes_api.create_recipient_view(
                account_id=self.account_id,
                envelope_id=envelope_id,
                recipient_view_request=view_request
            )
            return recipient_view.url
        except Exception as e:
            print(f"Error creating recipient view: {e}")
            return None


def docusign_embedded_signing_workflow(
    pdf_path: str,
    signer_email: str,
    signer_name: str,
    client_user_id: str = "1234"
) -> Optional[str]:
    """
    Complete DocuSign embedded signing workflow:
    - Authenticate
    - Create envelope
    - Get recipient view URL
    Returns the embedded signing URL or None on failure.
    """
    client = DocuSignClient()
    if not client.authenticate():
        print("Authentication failed.")
        return None
    envelope_id = client.create_envelope(
        pdf_path=pdf_path,
        signer_email=signer_email,
        signer_name=signer_name,
        client_user_id=client_user_id
    )
    if not envelope_id:
        print("Envelope creation failed.")
        return None
    view_url = client.create_recipient_view(
        envelope_id=envelope_id,
        signer_email=signer_email,
        signer_name=signer_name,
        client_user_id=client_user_id
    )
    if not view_url:
        print("Recipient view creation failed.")
        return None
    return view_url


if __name__ == "__main__":
    # Example usage
    pdf_path = "C:\\Projects\\Founders-AI\\talkdoc_core\\pdfs\\anlage_vm.pdf"
    signer_email = "rachana1897@gmail.com"
    signer_name = "Rachana Niranjan Murthy"
    view_url = docusign_embedded_signing_workflow(
        pdf_path=pdf_path,
        signer_email=signer_email,
        signer_name=signer_name
    )
    if view_url:
        print(f"Embedded signing URL: {view_url}")
    else:
        print("Failed to generate embedded signing URL.")