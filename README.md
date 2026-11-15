# OuraAppleHealth

Apple Shortcuts for exporting Oura data to Apple Health using the _V2 API_.

## Table of contents

1. [Introduction](#introduction)
   1. [Set-up](#set-up)
2. [Notes](#notes)
   1. [Continuous Heart Rate Variability](#hrv)
   2. [Lowest Resting Heart Rate](#rhr)
   3. [Body Temperature](#temp)
   4. [Blood Oxygen Saturation](#spo2)
3. [Contributing](#contributing)

## Introduction <a name="introduction"></a>

These shortcuts aim to export five data types from Oura to Health (click the links below to download each shortcut).

- [Average Heart Rate Variability](https://www.icloud.com/shortcuts/1b1023a29d514d25bbfdcb7e40f63531) (__Single__ averaged nightly value; read [notes](#hrv))
- [Continuous Heart Rate Variability](https://www.icloud.com/shortcuts/66849a9e5b584ce1ad48912266f8136f) (__All__ recorded nightly values; read [notes](#hrv))
- [Historical Continuous Heart Rate Variability](https://www.icloud.com/shortcuts/7713d2103b704a95a825f0a73557d0c7) (Imports historical HRV values; read [notes](#hrv))
- [Lowest Resting Heart Rate](https://www.icloud.com/shortcuts/53e063d2f99249cfb10aed02acb24ec8)
- [Body Temperature](https://www.icloud.com/shortcuts/53e6629a3ae6442d8e3d31b472c2d6c2)
- [Blood Oxygen Saturation](https://www.icloud.com/shortcuts/550e3e9a53df46c6a3c2c9f2baaefd0b)

> [!IMPORTANT]
> These shortcuts are **not** a way to get around the Oura Subscription, they need to be able to access the Oura API, which is only possible **with** a subscription. Note that for _Generation 2_ users this should not be a requirement, only for _Generation 3/4/5_ users.

### Set-up with OAuth (recommended) <a name="set-up"></a>

Oura is retiring Personal Access Tokens. The shortcuts in [`oauth/`](oauth) use OAuth2 instead. They refresh their own access with a token saved in iCloud Drive, so you only sign in once.

**1. Create an Oura application**

1. Go to [developer.ouraring.com](https://developer.ouraring.com) and create an application.
2. Open the application's details and set the **Redirect URI** to exactly `http://localhost`.
3. Keep the Client ID and Client Secret available. Treat the secret like a password.

**2. Sign the shortcuts on a Mac**

iPhone and iPad only import signed shortcut files, and signing needs a Mac (macOS 12 or later).

1. Download or clone this repository on the Mac.
2. In Terminal, run `bash oauth/sign.sh` from the repository folder.
3. Send the files in `oauth/signed/` to your iPhone (AirDrop, or copy them to iCloud Drive) and open each one to import it.

**3. Connect your Oura account**

1. Run **Oura Setup** on the iPhone.
2. Enter the Client ID and Client Secret.
3. Safari opens the Oura sign in page. Sign in and tap Allow.
4. Safari then shows a page that cannot load. That is expected. Copy the full address from the address bar (it starts with `http://localhost/?code=`), go back to Shortcuts, and paste it into the prompt. The code expires after a few minutes.
5. You should see "Oura is connected". Your credentials are stored in `iCloud Drive/Shortcuts/oura_auth.json`.

**4. Automate**

Set up an [_automation_](https://support.apple.com/guide/shortcuts/create-a-new-personal-automation-apdfbdbd7123/ios) that runs the data shortcuts **one after another in a single automation**. Oura refresh tokens can only be used once, so two shortcuts refreshing at the same moment would break the chain. If a shortcut reports "Oura token refresh failed", run Oura Setup again.

> [!NOTE]
> To rebuild the OAuth shortcuts after changing the originals, run `python3 tools/build_oauth.py`. It reads the signed shortcuts in the repository root, replaces the API key block with the OAuth token refresh, and writes unsigned files to `oauth/unsigned/`.

### Set-up with a Personal Access Token (legacy)

This only works while Oura still accepts Personal Access Tokens.

1. Download the desired shortcuts as linked in the introduction
2. Generate an Oura _Personal Access Token_ (API key) [here](https://cloud.ouraring.com/personal-access-tokens)
3. Add your key to the top of each shortcut (open up the shortcut in the app and there is a 'Text' block where the key should be pasted)
4. Set up an [_automation_](https://support.apple.com/guide/shortcuts/create-a-new-personal-automation-apdfbdbd7123/ios) in the Shortcuts App to run these shortcuts automatically every day

Done!

> [!TIP]
> These shortcuts can only run once you have opened the app in the morning to sync your sleep data. Therefore it is recommended to set the automation to run at a time when you know you will have opened the Oura app, or the scripts will fail to run. It is suggested to set the time for sometime in the afternoon, unless you tend to sync your data as soon as you get up. The data is written as if it was added at 6 am every morning, because this is generally the midpoint of my sleep, you may want to change this to be earlier or later. At some point I may alter it so that the shortcut calculates the midpoint of the sleep period and then writes it to that time.

> [!NOTE]
> These shortcuts are designed for iPhone, and will not run on MacOS as there is no native Apple Health API available.

> [!NOTE]
> The Shortcuts app must have explicit permission to write data to the Health app for each of the samples (HRV, SpO2, etc.). If Shortcuts has never attempted to write to Health before, this option will not be available in the Health permissions settings. To fix this, run the shortcut manually, allow it to fail, and return to the Health permissions settings to enable the appropriate permissions. At this point, your automation should work as expected. You can access the Health permissions settings by going to the Health app, selecting your profile in the top right, selecting 'Apps' under the 'Privacy' section, and then selecting 'Shortcuts.'.

## Notes <a name="notes"></a>

### Heart Rate Variability <a name="hrv"></a>

Two nightly shortcuts are available.
- _Continuous_ pulls all values recorded by Oura for a sleep period (usually logged every five minutes). Thanks to [@exhibiton](https://github.com/exhibiton) for this shortcut.
- _Average_ pulls only the average HRV for the night.

#### Historical Data

Use the `HRV Continuous Historical Data` to import data into Health for the previous 80 days. Thanks to [@artgmolina](https://github.com/artgmolina) for this shortcut.

> [!TIP]
> Change the number of days in the `Subtract x days from Current Date` code block to import data from further into the past. Note that your mileage may vary with how far back you can pull data. 

> [!CAUTION]
> Note that __only one__ of _Continuous_ or _Average_ HRV shortcuts should be used.

### Lowest Resting Heart Rate <a name="rhr"></a>

This pulls the single **lowest** heart rate captured over the night, and logs it as _Resting Heart Rate_ in Apple Health. This is different to the _Heart Rate_ metric, which Oura automatically syncs to Health.

### Body Temperature <a name="temp"></a>

There is no _Skin Temperature_ metric in Apple Health, which is what Oura measures. Instead, this shortcuts adds 37 celsius to the temperature change recorded in Oura, and logs it to the _Body temperature_ metric. This evidently isn't that scientific, but this allows you to identify trends easily in the Health app, particularly as negative temperature values are not allowed for obvious reasons. The value can be changed from 37 to an alternative number in the shortcut if that is more preferable.

> [!NOTE]
> Oura _should_ store temperature data in celsius, not fahrenheit, so 37C should automatically translate to 98.6F if you use non-metric units in Health/Oura. Please let me know if this is not the case.

### Blood Oxygen Saturation <a name="spo2"></a>

Oura have finally added this to the V2 API; the API docs in general are also getting much better. Note that Health may show decimals for the percentage. This is expected as Oura automatically rounds data in the app, but exists as the _true_ decimal value within the data on Oura Cloud (which the API pulls from).

> [!CAUTION]
> If you previosuly generated a key (personal access token) for use with the V1 API (or earlier versions of the V2 API), you will need to **generate a new token** for the shortcuts to be able to access blood oxygen data.

## Contributing <a name="contributing"></a>

If you would like to contribute to the shortcuts, please fork this repo and create a _Pull request_ which will be reviewed.

Alternatively, if you have an issue or suggestion, please create an _Issue_ for this repo.
