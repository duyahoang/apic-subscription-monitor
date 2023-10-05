# APIC Subscription Monitor

## Overview
This script is designed to monitor changes in a Cisco APIC using websockets. It establishes a websocket connection to the APIC and subscribes to queries defined in the configuration YAML file. Once subscribed, it listens for and processes updates, logging them to a file. This allows users to keep track of modifications in real time.

## Features
- Real-time monitoring: The script provides real-time updates on changes from the APIC environment through WebSocket Subscription.
- Short-time Object Buffering: Objects are buffered (1 second) during state transitions to ensure accuracy.
  - With deleted changes, the script is delayed another second, so the audit logs are populated at the top system level.
- Because of configuration changes of an object, the APIC implicitly creates/modifies/deletes other objects related to the configured object behind the scenes. Those objects are updated via the Subscription as well. The script provides a filtering mode (`filter_mode` in the configuration) that reduces the "noise" classes:
  - `whitelist`: Logs only events from classes specified in `whitelisted_classes` list.
  - `blacklist`: Ignores events from classes specified in `blacklisted_classes` list.
  - `verbose`: Logs all events without any filtering.
- Logging: Changes and relevant details are written to `apic-subscription.log`, providing a consistent record of updates.
  - Detailed Logging Format: Each log entry provides comprehensive details including the Object's Distinguished Name (DN), Object attributes, Description of the change, the Change Set that encompasses all modifications, and the User who made the change.
```
[Timestamp] [INFO] Created/Modified/Deleted - "dn":"Object's DN"
                                              "Object Attributes in JSON format"
                                              Description: 
                                              Change Set: 
                                              User: admin
```

## Prerequisites

### Python version Required
- Python 3.7 and above.
- Python and Pip commands can be `python` or `python3` and `pip` or `pip3` depending on the compute environment.

### Packages Dependencies
- `aiohttp`
- `websockets`
- `yaml`
```
pip install aiohttp websockets pyyaml
```

## Configuration YAML file
Configuration details such as username, password, APIC URL, and queries to monitor should be specified in the `apic-subscription-config.yaml` file. If a password is not provided in the configuration, the script will prompt the user for it.
```
apic: <APIC IP or FQDN>
username: <APIC username>
password: <optional APIC password>
queries:
  - api_ep: <API endpoint to subscribe>
    filters: <optional filters for the API endpoint>
filter_mode: <whitelist|blacklist|verbose>
whitelisted_classes:
  - <list of classes to allow if in whitelist mode>
blacklisted_classes:
  - <list of classes to ignore if in blacklist mode>
```

## How to use
1. Ensure you have all the necessary packages installed.
2. Set up the `apic-subscription-config.yaml` configuration file.
3. Run the script using `python <script-name>.py`.
4. Monitor the `apic-subscription.log` for real-time updates and logs.

## Shutdown script
The script handles SIGTERM and SIGINT signals to shut down gracefully. If you want to stop the script, you can use Ctrl + C or send a termination signal. It will ensure that all asynchronous tasks are properly canceled before shutting down.

## Example
Terminal
```
python3 apic-subscription-monitor.py
Logs are being written to 'apic-subscription.log'. Please monitor this file for updates.
```

apic-subscription.log (with verbose filter mode)
```
[2023-10-04 21:56:26] [INFO] https://10.201.36.113/api/class/fvTenant.json?subscription=yes&query-target=subtree - Subscription ID: 72057997783531521
[2023-10-04 21:56:28] [INFO] https://10.201.36.113/api/class/infraInfra.json?subscription=yes&query-target=subtree - Subscription ID: 72057997783531522
[2023-10-04 21:56:47] [INFO] Created - "dn":"uni/tn-dh-ansible-aac/BD-BD_VLAN100/rtbd-[uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg]"
                                     {'fvRtBd': {'attributes': {'childAction': '', 'dn': 'uni/tn-dh-ansible-aac/BD-BD_VLAN100/rtbd-[uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg]', 'lcOwn': 'local', 'modTs': '2023-10-05T05:06:15.704+00:00', 'rn': '', 'status': 'created', 'tCl': 'fvAEPg', 'tDn': 'uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg'}}}
[2023-10-04 21:56:47] [INFO] Created - "dn":"uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg/rsbd/subnetBddefDn-[uni/bd-[uni/tn-dh-ansible-aac/BD-BD_VLAN100]-isSvc-no]"
                                     {'fvSubnetBDDefCont': {'attributes': {'bddefDn': 'uni/bd-[uni/tn-dh-ansible-aac/BD-BD_VLAN100]-isSvc-no', 'childAction': '', 'dn': 'uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg/rsbd/subnetBddefDn-[uni/bd-[uni/tn-dh-ansible-aac/BD-BD_VLAN100]-isSvc-no]', 'lcOwn': 'local', 'modTs': '2023-10-05T05:06:15.704+00:00', 'monPolDn': 'uni/tn-common/monepg-default', 'name': '', 'nameAlias': '', 'rn': '', 'status': 'created'}}}
[2023-10-04 21:56:47] [INFO] Created - "dn":"uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg/rscustQosPol"
                                     {'fvRsCustQosPol': {'attributes': {'annotation': '', 'childAction': '', 'dn': 'uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg/rscustQosPol', 'extMngdBy': '', 'forceResolve': 'yes', 'lcOwn': 'local', 'modTs': '2023-10-05T05:06:15.764+00:00', 'monPolDn': 'uni/tn-common/monepg-default', 'rType': 'mo', 'rn': '', 'state': 'formed', 'stateQual': 'default-target', 'status': 'created', 'tCl': 'qosCustomPol', 'tContextDn': '', 'tDn': 'uni/tn-common/qoscustom-default', 'tRn': 'qoscustom-default', 'tType': 'name', 'tnQosCustomPolName': '', 'uid': '0'}}}
                                     Description: RsCustQosPol deleted
                                     User: admin
[2023-10-04 21:56:47] [INFO] Created - "dn":"uni/tn-common/qoscustom-default/rtfvCustQosPol-[uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg]"
                                     {'qosRtCustQosPol': {'attributes': {'childAction': '', 'dn': 'uni/tn-common/qoscustom-default/rtfvCustQosPol-[uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg]', 'lcOwn': 'local', 'modTs': '2023-10-05T05:06:15.809+00:00', 'rn': '', 'status': 'created', 'tCl': 'fvAEPg', 'tDn': 'uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg'}}}
[2023-10-04 21:56:47] [INFO] Created - "dn":"uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg/rsbd"
                                     {'fvRsBd': {'attributes': {'annotation': '', 'childAction': '', 'dn': 'uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg/rsbd', 'extMngdBy': '', 'forceResolve': 'yes', 'lcOwn': 'local', 'modTs': '2023-10-05T05:06:15.704+00:00', 'monPolDn': 'uni/tn-common/monepg-default', 'rType': 'mo', 'rn': '', 'state': 'formed', 'stateQual': 'none', 'status': 'created', 'tCl': 'fvBD', 'tContextDn': '', 'tDn': 'uni/tn-dh-ansible-aac/BD-BD_VLAN100', 'tRn': 'BD-BD_VLAN100', 'tType': 'name', 'tnFvBDName': 'BD_VLAN100', 'uid': '0'}}}
                                     Description: RsBd deleted
                                     User: admin
[2023-10-04 21:56:48] [INFO] Created - "dn":"uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg"
                                     {'fvAEPg': {'attributes': {'annotation': '', 'childAction': '', 'configIssues': '', 'configSt': 'applied', 'descr': '', 'dn': 'uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg', 'exceptionTag': '', 'extMngdBy': '', 'floodOnEncap': 'disabled', 'fwdCtrl': '', 'hasMcastSource': 'no', 'isAttrBasedEPg': 'no', 'isSharedSrvMsiteEPg': 'no', 'lcOwn': 'local', 'matchT': 'AtleastOne', 'modTs': '2023-10-05T05:06:15.738+00:00', 'monPolDn': 'uni/tn-common/monepg-default', 'name': 'dh-epg', 'nameAlias': '', 'pcEnfPref': 'unenforced', 'pcTag': '32772', 'prefGrMemb': 'exclude', 'prio': 'unspecified', 'rn': '', 'scope': '2785286', 'shutdown': 'no', 'status': 'created', 'triggerSt': 'triggerable', 'txId': '17870283321425322022', 'uid': '15374'}}}
                                     Description: RsCustQosPol deleted
                                                  RsBd deleted
                                                  AEPg dh-epg deleted
                                     User: admin
[2023-10-04 21:57:34] [INFO] Created - "dn":"uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg/rsbd/subnetBddefDn-[uni/bd-[uni/tn-dh-ansible-aac/BD-BD_VLAN101]-isSvc-no]"
                                     {'fvSubnetBDDefCont': {'attributes': {'bddefDn': 'uni/bd-[uni/tn-dh-ansible-aac/BD-BD_VLAN101]-isSvc-no', 'childAction': '', 'dn': 'uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg/rsbd/subnetBddefDn-[uni/bd-[uni/tn-dh-ansible-aac/BD-BD_VLAN101]-isSvc-no]', 'lcOwn': 'local', 'modTs': '2023-10-05T05:07:01.088+00:00', 'monPolDn': 'uni/tn-common/monepg-default', 'name': '', 'nameAlias': '', 'rn': '', 'status': 'created'}}}
[2023-10-04 21:57:34] [INFO] Created - "dn":"uni/tn-dh-ansible-aac/BD-BD_VLAN101/rtbd-[uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg]"
                                     {'fvRtBd': {'attributes': {'childAction': '', 'dn': 'uni/tn-dh-ansible-aac/BD-BD_VLAN101/rtbd-[uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg]', 'lcOwn': 'local', 'modTs': '2023-10-05T05:07:01.088+00:00', 'rn': '', 'status': 'created', 'tCl': 'fvAEPg', 'tDn': 'uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg'}}}
[2023-10-04 21:57:34] [INFO] Modified - "dn":"uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg/rsbd"
                                      {'fvRsBd': {'attributes': {'childAction': '', 'dn': 'uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg/rsbd', 'modTs': '2023-10-05T05:07:01.088+00:00', 'rn': '', 'state': 'formed', 'status': 'modified', 'tDn': 'uni/tn-dh-ansible-aac/BD-BD_VLAN101', 'tRn': 'BD-BD_VLAN101', 'tnFvBDName': 'BD_VLAN101'}}}
                                      Description: RsBd modified
                                      Change Set: tnFvBDName (Old: BD_VLAN100, New: BD_VLAN101)
                                      User: admin
[2023-10-04 21:57:35] [INFO] Deleted - "dn":"uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg/rsbd/subnetBddefDn-[uni/bd-[uni/tn-dh-ansible-aac/BD-BD_VLAN100]-isSvc-no]"
                                     {'fvSubnetBDDefCont': {'attributes': {'childAction': '', 'dn': 'uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg/rsbd/subnetBddefDn-[uni/bd-[uni/tn-dh-ansible-aac/BD-BD_VLAN100]-isSvc-no]', 'modTs': '2023-10-05T05:07:01.088+00:00', 'rn': '', 'status': 'deleted'}}}
[2023-10-04 21:57:35] [INFO] Deleted - "dn":"uni/tn-dh-ansible-aac/BD-BD_VLAN100/rtbd-[uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg]"
                                     {'fvRtBd': {'attributes': {'childAction': '', 'dn': 'uni/tn-dh-ansible-aac/BD-BD_VLAN100/rtbd-[uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg]', 'modTs': '2023-10-05T05:07:01.088+00:00', 'rn': '', 'status': 'deleted'}}}
[2023-10-04 21:57:45] [INFO] Deleted - "dn":"uni/tn-common/qoscustom-default/rtfvCustQosPol-[uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg]"
                                     {'qosRtCustQosPol': {'attributes': {'childAction': '', 'dn': 'uni/tn-common/qoscustom-default/rtfvCustQosPol-[uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg]', 'modTs': '2023-10-05T05:07:10.674+00:00', 'rn': '', 'status': 'deleted'}}}
[2023-10-04 21:57:45] [INFO] Deleted - "dn":"uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg/rsbd"
                                     {'fvRsBd': {'attributes': {'childAction': '', 'dn': 'uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg/rsbd', 'modTs': '2023-10-05T05:07:10.647+00:00', 'rn': '', 'status': 'deleted'}}}
                                     Description: RsBd deleted
                                     User: admin
[2023-10-04 21:57:45] [INFO] Deleted - "dn":"uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg/rscustQosPol"
                                     {'fvRsCustQosPol': {'attributes': {'childAction': '', 'dn': 'uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg/rscustQosPol', 'modTs': '2023-10-05T05:07:10.647+00:00', 'rn': '', 'status': 'deleted'}}}
                                     Description: RsCustQosPol deleted
                                     User: admin
[2023-10-04 21:57:45] [INFO] Deleted - "dn":"uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg/rsbd/subnetBddefDn-[uni/bd-[uni/tn-dh-ansible-aac/BD-BD_VLAN101]-isSvc-no]"
                                     {'fvSubnetBDDefCont': {'attributes': {'childAction': '', 'dn': 'uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg/rsbd/subnetBddefDn-[uni/bd-[uni/tn-dh-ansible-aac/BD-BD_VLAN101]-isSvc-no]', 'modTs': '2023-10-05T05:07:10.647+00:00', 'rn': '', 'status': 'deleted'}}}
[2023-10-04 21:57:45] [INFO] Deleted - "dn":"uni/tn-dh-ansible-aac/BD-BD_VLAN101/rtbd-[uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg]"
                                     {'fvRtBd': {'attributes': {'childAction': '', 'dn': 'uni/tn-dh-ansible-aac/BD-BD_VLAN101/rtbd-[uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg]', 'modTs': '2023-10-05T05:07:10.647+00:00', 'rn': '', 'status': 'deleted'}}}
[2023-10-04 21:57:45] [INFO] Deleted - "dn":"uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg"
                                     {'fvAEPg': {'attributes': {'childAction': '', 'dn': 'uni/tn-dh-ansible-aac/ap-dh-ap/epg-dh-epg', 'modTs': '2023-10-05T05:07:10.647+00:00', 'pcTag': 'any', 'rn': '', 'scope': '0', 'status': 'deleted'}}}
                                     Description: AEPg dh-epg deleted
                                     User: admin
[2023-10-04 21:58:01] [INFO] Received exit signal SIGINT...
[2023-10-04 21:58:01] [INFO] Cancelling 7 tasks

```

## License

This project is open-source and available under the MIT License. See the LICENSE file for more info.
