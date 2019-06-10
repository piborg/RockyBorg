#!/bin/bash

DUB=`pwd`

echo '=== Installing prerequisites ==='
sudo apt-get update
sudo apt-get -y install i2c-tools tix
sudo pip3 install opencv-python
sudo apt-get -y install libcblas-dev libatlas-base-dev libjasper-dev libqtgui4 libqt4-test

echo '=== Removing I2C devices from the blacklisting ==='
sudo cp /etc/modprobe.d/raspi-blacklist.conf /etc/modprobe.d/raspi-blacklist.conf.old
sudo sed -i 's/^blacklist i2c-bcm2708/#\0    # We need this enabled for I2C add-ons, e.g. PicoBorg Reverse/g' /etc/modprobe.d/raspi-blacklist.conf

echo '=== Adding I2C devices to auto-load at boot time ==='
sudo cp /etc/modules /etc/modules.old
sudo sed -i '/^\s*i2c-dev\s*/d' /etc/modules
sudo sed -i '/^\s*i2c-bcm2708\s*/d' /etc/modules
sudo sed -i '/^#.*RockyBorg.*/d' /etc/modules
sudo bash -c "echo '' >> /etc/modules"
sudo bash -c "echo '# Kernel modules needed for I2C add-ons, e.g. RockyBorg' >> /etc/modules"
sudo bash -c "echo 'i2c-dev' >> /etc/modules"
sudo bash -c "echo 'i2c-bcm2708' >> /etc/modules"

echo '=== Adding user "pi" to the I2C permissions list ==='
sudo adduser pi i2c

echo '=== Make scripts executable ==='
chmod a+x *.py
chmod a+x *.sh

echo '=== Create a desktop shortcut for the testing GUI ==='
UB_SHORTCUT="${HOME}/Desktop/RockyBorg.desktop"
echo "[Desktop Entry]" > ${UB_SHORTCUT}
echo "Encoding=UTF-8" >> ${UB_SHORTCUT}
echo "Version=1.0" >> ${UB_SHORTCUT}
echo "Type=Application" >> ${UB_SHORTCUT}
echo "Exec=${DUB}/rbTestGui.py" >> ${UB_SHORTCUT}
echo "Icon=${DUB}/piborg.ico" >> ${UB_SHORTCUT}
echo "Terminal=false" >> ${UB_SHORTCUT}
echo "Name=RockyBorg Testing GUI" >> ${UB_SHORTCUT}
echo "Comment=RockyBorg motor and servo test GUI" >> ${UB_SHORTCUT}
echo "Categories=Application;Development;" >> ${UB_SHORTCUT}

echo '=== Create a desktop shortcut for the tuning GUI ==='
UB_SHORTCUT="${HOME}/Desktop/RockyBorgTuning.desktop"
echo "[Desktop Entry]" > ${UB_SHORTCUT}
echo "Encoding=UTF-8" >> ${UB_SHORTCUT}
echo "Version=1.0" >> ${UB_SHORTCUT}
echo "Type=Application" >> ${UB_SHORTCUT}
echo "Exec=${DUB}/rbTuningGui.py" >> ${UB_SHORTCUT}
echo "Icon=${DUB}/piborg.ico" >> ${UB_SHORTCUT}
echo "Terminal=false" >> ${UB_SHORTCUT}
echo "Name=RockyBorg Tuning GUI" >> ${UB_SHORTCUT}
echo "Comment=RockyBorg Tuning GUI" >> ${UB_SHORTCUT}
echo "Categories=Application;Development;" >> ${UB_SHORTCUT}

echo '=== Finished ==='
echo ''
echo 'Your Raspberry Pi should now be setup for running RockyBorg'
echo 'Please restart your Raspberry Pi to ensure the I2C driver is running'
