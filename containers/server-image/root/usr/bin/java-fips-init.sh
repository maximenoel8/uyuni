#!/bin/bash
# Configure Java's strong SecureRandom when running on a FIPS-enabled host.
#
# On a FIPS host the JDK enters FIPS mode and disables the SUN SecureRandom
# implementations (NativePRNGBlocking, DRBG), but neither the JDK nor the
# crypto-policies java backend repoints "securerandom.strongAlgorithms" at the
# NSS FIPS provider. As a result SecureRandom.getInstanceStrong() that was called by
# the pgjdbc-ng driver during SCRAM-SHA-256 auth, fails with
# "No strong SecureRandom impls available". We supply the missing value here.
#
# The NSS FIPS provider (SunPKCS11-NSS-FIPS) is auto-configured by the JDK via
# conf/security/nss.fips.cfg, and NSS enters FIPS mode automatically through
# mozilla-nss-sysinit based on /proc/sys/crypto/fips_enabled 

# On non-FIPS hosts that provider does not exist, so we must NOT set the
# property there. we write an empty override file instead (a no-op), which the
# JVM always loads via JDK_JAVA_OPTIONS.

OVERRIDE_FILE="/etc/java/security/fips-securerandom.security"
FIPS_ENABLED=$(cat /proc/sys/crypto/fips_enabled 2>/dev/null || echo 0)

mkdir -p /etc/java/security

if [ "$FIPS_ENABLED" = "1" ]; then
    echo 'securerandom.strongAlgorithms=PKCS11:SunPKCS11-NSS-FIPS' > "$OVERRIDE_FILE"
else
    # Empty file: JDK_JAVA_OPTIONS always references it, so it must exist.
    > "$OVERRIDE_FILE"
fi
