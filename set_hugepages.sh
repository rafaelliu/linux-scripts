#!/bin/bash

# Script developed for configuring HugePages on RHEL, based on https://access.redhat.com/site/node/46326
#
# Rafael Liu <rliu@redhat.com>

# user to run the process
JAVA_USER="rliu"

# memory reserved to OS (bytes)
OS_MEM=$(( 1 * 1024 * 1024 * 1024 )) #1G

#
# you shouldn't mess below
#

set_config() {
        KEY="$1"
        VALUE="$2"
        FILE="$3"
        sed -i "s/$KEY\s*=.*/$KEY=$VALUE/g" $FILE

        if [ ! $( grep "$KEY=$VALUE" $FILE ) ]; then
                echo "$KEY=$VALUE" >> $FILE
        fi
}

get_memproc_prop() {
	grep $1 $PROC_MEM | awk ' { print $2 }'
}

set_sysctl() {
	set_config $1 $2 $SYSCTL_FILE
}

# user's gid
GROUP_ID=$( id -g $JAVA_USER) || { echo "* User doesn't exist"; exit 1; }

# files to be changed
SYSCTL_FILE="/etc/sysctl.conf"
LIMITS_DIR="/etc/security/limits.d"
PROC_MEM="/proc/meminfo"

# size of hugepages in bytes
HUGEPAGE_SIZE=$( get_memproc_prop Hugepagesize ) || { echo "* Kernel doesn't support HugePages"; exit 1; } # KB
HUGEPAGE_SIZE=$(( $HUGEPAGE_SIZE * 1024 )) # to B

# total memory of the OS
TOTAL_MEM=$( get_memproc_prop MemTotal ) # KB
TOTAL_MEM=$(( $TOTAL_MEM * 1024 )) # to B

# number of hugepages to be created
NUMBER_PAGES=$(( ( $TOTAL_MEM - $OS_MEM ) / $HUGEPAGE_SIZE ))

if [[ $NUMBER_PAGES < 0 ]]; then
	echo "* The OS_MEM should be less than total OS memory"
	exit 1;
fi

# total of memory locked in kbytes
MEM_LOCK=$(( $NUMBER_PAGES * $HUGEPAGE_SIZE / 1024 )) #KB

# configure hugepages
set_sysctl kernel.shmmax $TOTAL_MEM
set_sysctl vm.nr_hugepages $NUMBER_PAGES
set_sysctl vm.hugetlb_shm_group $GROUP_ID

sysctl -p

if [[ $( get_memproc_prop HugePages_Total ) != $NUM_PAGES ]]; then
	echo "* It wasn't possible to apply HugePages configuration"
	exit 1
fi

# configure locks
cat > $LIMITS_DIR/$JAVA_USER-hugepages.conf <<-EOF
	$JAVA_USER     soft     memlock     $MEM_LOCK
	$JAVA_USER     hard     memlock     $MEM_LOCK
EOF

exit 0

