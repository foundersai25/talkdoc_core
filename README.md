# Project Name

A Streamlit-based chat application.

## Installation

1. **Clone the repository**
    ```bash
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    ```

2. **Install talkdoc_core **
    ```bash
    pip install .
    ```

3. **Run the Streamlit app**
    ```bash
    streamlit run Chat.py
    ```

4. **To scan a document image in the interactive mode, use the following command:**
    ```bash
    python talkdoc_core/scanner.py --image images/sample6.jpg -i
    ```

5. **To scan all images in a directory automatically, use the following command:**
    ```bash
    python talkdoc_core/scanner.py --images images
    ```

6. **To Use Docusign API**
    1. Create a Docusign Developer Account at [Docusign Developer](https://developers.docusign.com/)
    2. Create an App and get the following details:
        - Client ID
        - Client Secret
        - Account ID
        - Impersonated User GUID (API Username)
    3. Generate a RSA Keypair and add the private key to the project directory (e.g., `private.key`).
    4. Update the `.env` file with the Docusign credentials. You can use the provided `.env.example` as a template.
    ```plaintext
    DS_CLIENT_ID=your_client_id
    DS_ACCOUNT_ID=your_account_id
    DS_CLIENT_SECRET=your_client_secret
    DS_IMPERSONATED_USER_GUID=your_impersonated_user_guid
    DS_PRIVATE_KEY_PATH=path_to_your_private_key_file
    ```
    5. Ensure the redirect URI in your Docusign app settings matches the one in your `.env` file (e.g., `http://localhost:8080/`).
    6. Run the Streamlit app and authenticate with Docusign when prompted.
    7. If Authentication doesn't work, follow the steps in the [Docusign OAuth Guide](https://developers.docusign.com/platform/auth/authcode/authcode-get-token/).

