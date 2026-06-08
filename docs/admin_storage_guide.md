# SPARSH - Storage Configuration Guide (Administrator)

SPARSH allows you to automatically save generated student report cards (PDFs) directly to your Google Drive, or to the local server disk. This guide walks you through the setup process.

---

## Choosing a Storage Provider

SPARSH supports two storage providers:

1. **Local Storage**: Saves report cards directly on the computer/server running SPARSH. This requires zero setup and is the default option.
2. **Google Drive**: Saves report cards to a specific folder in your Google Drive. This makes reports accessible from anywhere and backs them up in the cloud.

---

## How to Connect Google Drive

Connecting Google Drive is a simple, secure process. You authorize SPARSH to access your Drive using your own Google account.

### Step 1: Connect your Google Account

1. Log in to SPARSH as an Administrator.
2. Navigate to **Settings** -> **Storage Settings**.
3. Under "Configure Storage", select **Google Drive**.
4. In the "Step 1: Connect Google Account" section, click the **Connect Google Drive** button.
5. A new window will open asking you to sign in to Google. Choose the account where you want to store the report cards.
6. Google will ask you to grant SPARSH permission to "See, edit, create, and delete only the specific Google Drive files you use with this app." Click **Allow**.
    *   *Note: If you see a warning that says "Google hasn't verified this app", click **Advanced** at the bottom, then click **Go to SPARSH (unsafe)** to proceed.*
7. You will be redirected back to SPARSH, and Step 1 should now show a green checkmark indicating your account is connected.

### Step 2: Select a Drive Folder

You must tell SPARSH *where* in your Google Drive to save the files.

1. Open a new browser tab and go to [Google Drive](https://drive.google.com).
2. Navigate to the folder you want to use, or create a new one (e.g., "SPARSH Report Cards").
3. Double-click the folder to open it.
4. Copy the URL from your browser's address bar. It should look something like this: `https://drive.google.com/drive/folders/1A2b3C4d5E6f7G8h9I0jK-L_MnOpQrStU`
5. Go back to the SPARSH Storage Settings page.
6. In "Step 2: Select Drive Folder", paste the URL into the **Google Drive Folder URL** field.

### Step 3: Verify and Test

1. Click the **Verify Folder** button. SPARSH will check if it can read the folder. A success message will appear with the folder's name.
2. A **Test Upload** button will appear. Click it. SPARSH will create a temporary text file in your folder and immediately delete it, proving it has write access.
3. If both verification and testing are successful, the **Save Settings** button will be enabled.

### Step 4: Save

1. Click **Save Settings** at the bottom right.
2. The Current Status Panel at the top of the page will update to show "Google Drive" as the operational provider.

All future report cards uploaded via the "Historical Reports" module will now be saved to your specified Google Drive folder.

---

## Disconnecting Google Drive

If you want to stop using Google Drive or switch to a different Google account:

1. Go to the Storage Settings page.
2. In the "Step 1" section, click the **Disconnect** button.
3. The connection will be removed. You can now connect a different account or switch the Storage Provider back to "Local Storage" and click **Save Settings**.
