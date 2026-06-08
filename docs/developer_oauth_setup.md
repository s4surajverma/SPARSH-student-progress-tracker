# SPARSH - Google Drive OAuth Setup Guide (Developer)

This guide is for **Developers** only. School administrators do not need to perform these steps.

As a developer, you must configure a Google Cloud Project to act as the OAuth 2.0 Identity Provider. This is a one-time setup process. Once configured, all SPARSH instances can use these credentials to allow admins to connect their own Google Drive accounts.

## Prerequisites
- A Google Account
- Access to the [Google Cloud Console](https://console.cloud.google.com/)

---

## Step 1: Create a Google Cloud Project
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Click the project dropdown in the top navigation bar and select **New Project**.
3. Name the project `SPARSH Storage Integration` (or similar) and click **Create**.
4. Select the newly created project.

## Step 2: Enable the Google Drive API
1. Navigate to **APIs & Services** > **Library** in the left sidebar.
2. Search for "Google Drive API".
3. Click on the result and click **Enable**.

## Step 3: Configure the Google Auth Platform
Google recently updated their UI. You will now see a section called **Google Auth Platform**.
1. Navigate to **APIs & Services** > **Google Auth Platform** (or **OAuth consent screen** if you see the old menu).
2. You will see a screen saying "Google auth platform not configured yet". Click the **Get started** button.
3. **App Information (Branding)**:
   - **App name**: `SPARSH`
   - **User support email**: Select your email address
   - **Developer contact information**: Enter your email address
   - Click **Next** or **Save and Continue**.
4. **Audience**:
   - Select **External** (unless your school has a strict Google Workspace setup and you only want internal users to access it).
   - If you select External, you may be asked to add **Test Users**. Add the email addresses of the school administrators who will be testing the app.
   - Click **Next**.
5. **Data Access (Scopes)**:
   - Click **Add or Remove Scopes**.
   - Search for the Google Drive API.
   - Check the box for the scope: `.../auth/drive.file` (Description: *See, edit, create, and delete only the specific Google Drive files you use with this app*).
   - *Do not* select the broad `/auth/drive` scope.
   - Click **Update** and then **Next**.
6. Review your settings and complete the wizard.

## Step 4: Create OAuth 2.0 Credentials
1. Navigate to **APIs & Services** > **Credentials**.
2. Click **Create Credentials** > **OAuth client ID**.
3. **Application Type**: Select **Web application**.
4. **Name**: `SPARSH Backend`.
5. **Authorized JavaScript origins**:
   - Leave blank for now, or add your domain if using a strictly separated frontend.
6. **Authorized redirect URIs**:
   - Add your development URL: `http://127.0.0.1:8000/api/v1/settings/storage/oauth/callback`
   - Add your production URL: `https://your-production-domain.com/api/v1/settings/storage/oauth/callback`
7. Click **Create**.
8. A modal will appear containing your **Client ID** and **Client Secret**.

## Step 5: Configure SPARSH Environment
1. Open the `.env` file in the SPARSH backend directory.
2. Populate the Google OAuth section with the credentials from Step 4:
   ```env
   # Google OAuth (Developer Setup)
   GOOGLE_CLIENT_ID="your-client-id-here"
   GOOGLE_CLIENT_SECRET="your-client-secret-here"
   GOOGLE_REDIRECT_URI="http://127.0.0.1:8000/api/v1/settings/storage/oauth/callback"
   ```
3. (In production, ensure `GOOGLE_REDIRECT_URI` matches the production URI you added in Step 4).

## Important Considerations
* **Refresh Token Lifespan**: If your OAuth Consent Screen is set to "External" and the publishing status is "Testing", refresh tokens issued to users will **expire after 7 days**. You must set the status to "In production" in the OAuth consent screen to get long-lived tokens.
* **Unverified App Warning**: If your app is set to "External" and you have not gone through Google's verification process, users will see a warning screen saying "Google hasn't verified this app." They can bypass this by clicking "Advanced" -> "Go to SPARSH". This is normal for internal tools that haven't been submitted for public review.
