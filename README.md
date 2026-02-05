# HomeChain Android Miner 📱⛏️

This is the official mobile miner for HomeChain, built with Python & Kivy.
It supports **BIP-39 Mnemonic Wallets** (12-word phrase) and connects directly to the HomeChain Node.

## Features
- **Create Wallet**: Generates a secure 12-word seed phrase.
- **Import Wallet**: Restore existing wallets using your mnemonic.
- **One-Click Mining**: Connects to the official node (`http://13.220.55.223`) automatically.
- **Real-time Stats**: Shows Hashrate and Mining Status.

## How to Build (APK)
You need a Linux environment (Ubuntu/WSL) to compile this application.

### 1. Install Dependencies
```bash
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
pip3 install --user --upgrade buildozer cython virtualenv
```

### 2. Build the APK
Navigate to this directory and run:

```bash
cd android_miner
buildozer android debug
```

### 3. Install
Once finished (approx. 15 mins), you will find the `.apk` file in the `bin/` folder.
Transfer it to your Android device and install!

## Requirements
- Android 8.0 or higher recommended.
- Internet connection (to communicate with Node).
