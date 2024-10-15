# Guide to Setting Up Google OAuth Credentials for Google Cloud


## Step 1: Set Up a Google Cloud Project
1. **Log in to Google Cloud Console**: Go to [Google Cloud Console](https://console.cloud.google.com/).
2. **Create a Project**:
   - Click on the **Select a project** dropdown.
   - Click **New Project**.
   - Give your project a name and click **Create**.

## Step 2: Enable Google Calendar API
1. **Navigate to API & Services**:
   - From the navigation menu, go to **APIs & Services > Library**.
2. **Search for Google Calendar API**:
   - Type "Google Calendar API" in the search bar.
   - Click on the **Google Calendar API** result and then click **Enable**.

## Step 3: Create Service Account Credentials
1. **Navigate to Service Accounts**:
   - Go to **APIs & Services > Credentials**.
   - Click **Create Credentials** and select **Service Account**.
2. **Configure the Service Account**:
   - Enter a **Service Account Name** and click **Create and Continue**.
   - Assign **Editor** role to the service account to allow creating calendar events.
   - Click **Done**.
3. **Generate a Key File**:
   - Under **APIs & Services > Credentials**, locate the service account you just created.
   - Click on the **Service Account** name, then go to the **Keys** tab.
   - Click **Add Key** and select **Create New Key**.
   - Choose **JSON** format and click **Create**.
   - The key file will be downloaded automatically. This file contains the credentials your script needs.

## Step 4: Save the Credentials File
1. **Store the JSON File Securely**:
   - Move the downloaded JSON key file to a secure location within your project.
   - It is recommended to store this file outside of your main source code directory for security reasons.

## Step 5: Set Up Environment Variables
 **Add variables to `.env` File**:
   - Add the following lines to your `.env` file:
     ```
     GOOGLE_AUTH_KEY="path/to/your/service_account_key.json"
     GOOGLE_CALENDAR_ID="your_calendar_id_here"
     ```
   - Replace `path/to/your/service_account_key.json` with the actual path to your JSON key file.
   - Replace `your_calendar_id_here` with the ID of your Google Calendar. Default calender ID is your gmail address.

## Step 6: Share Your Google Calendar with the Service Account
1. **Locate Service Account Email**:
   - In the Google Cloud Console, navigate to **APIs & Services > Credentials** and find the service account.
   - Copy the **email address** of the service account (it ends with `@your_project.iam.gserviceaccount.com`).
2. **Share Your Calendar**:
   - Go to [Google Calendar](https://calendar.google.com/).
   - Click on the **Settings** icon (gear icon), then click **Settings**.
   - Under **Settings for my calendars**, select the calendar you want to use.
   - Scroll down to **Share with specific people** and click **Add people**.
   - Paste the **service account email** and give it **Make changes to events** permission.

## Notes
- **Security**: Avoid committing the JSON key file or `.env` file to your version control system. Use `.gitignore` to prevent these files from being included in repositories.