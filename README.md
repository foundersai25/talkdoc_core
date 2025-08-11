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