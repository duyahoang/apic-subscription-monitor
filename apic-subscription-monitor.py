# flake8: noqa E501
import asyncio
import aiohttp
import logging
import websockets
import getpass
import ssl
import yaml
import signal
import json
from datetime import datetime


# --- Config & Logging ---

# Setting up basic logging configuration.
logging.basicConfig(
    filename="apic-subscription.log",
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",  # Format for the log messages.
    datefmt="%Y-%m-%d %H:%M:%S",  # Format for the date in log messages.
)


async def load_config(filename):
    # Loading the configuration from a YAML file.
    with open(filename, "r") as file:
        config = yaml.safe_load(file)

    # If the password is not in the configuration, prompt the user to enter it.
    if "password" not in config:
        config["password"] = getpass.getpass(prompt="Enter the password: ")

    # Setting the default filter mode to 'auto' if not provided in the config.
    config["filter_mode"] = config.get("filter_mode", "auto")

    return config


# --- APIC Authentication and Connection ---


async def get_auth_cookie(username, password, base_url):
    # Create the payload for the authentication request.
    payload = {"aaaUser": {"attributes": {"name": username, "pwd": password}}}
    url = f"{base_url}/api/aaaLogin.json"

    # Using aiohttp to send an asynchronous HTTP POST request to obtain authentication cookie.
    timeout = aiohttp.ClientTimeout(
        total=20
    )  # 20 seconds timeout for the entire connection process
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, json=payload, verify_ssl=False) as login_response:
            if login_response.status != 200:
                logging.warning(
                    f"Failed to Get APIC Token - Response Message: {await login_response.text()}"
                )
            # Parsing the response to extract the token and construct the cookie.
            response_dict = await login_response.json()
            token = response_dict["imdata"][0]["aaaLogin"]["attributes"]["token"]
            refresh_timeout = int(
                response_dict["imdata"][0]["aaaLogin"]["attributes"][
                    "refreshTimeoutSeconds"
                ]
            )
            cookie = {"APIC-cookie": token}
            # logging.info(f"Get APIC Token - Status Code: {login_response.status}")
    return cookie, refresh_timeout


async def refresh_cookie(username, password, base_url, cookie, refresh_timeout):
    await asyncio.sleep(refresh_timeout - 60)
    while True:
        new_cookie, refresh_timeout = await get_auth_cookie(
            username, password, base_url
        )
        cookie.clear()
        cookie.update(new_cookie)
        await asyncio.sleep(refresh_timeout - 60)


async def open_web_socket(apic, cookie):
    # Creating a websocket URL using the provided APIC and cookie.
    token = cookie.get("APIC-cookie")
    websocket_url = f"wss://{apic}/socket{token}"

    # Create a context with a specified protocol and set verify_mode to CERT_NONE.
    context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    # Establishing a websocket connection and returning the websocket object.
    ws = await websockets.connect(websocket_url, ssl=context)
    return ws


# --- WebSockets: Subscription & Message Processing ---


async def fetch_with_session(session, url, **kwargs):
    async with session.get(url, **kwargs) as response:
        return await response.json()


async def subscribe_to_queries(base_url, cookie, queries):
    # Initializing an empty dictionary to store the subscription IDs.
    query_to_subid = {}
    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=False)
    ) as session:
        for query in queries:
            url = f"{base_url}{query['api_ep']}.json?subscription=yes{query.get('filters', '')}"
            # Sending a GET request to subscribe to the queries and storing the subscription IDs.
            response_dict = await fetch_with_session(session, url, cookies=cookie)
            if "subscriptionId" in response_dict:
                subid = response_dict["subscriptionId"]
                query_to_subid[query["api_ep"]] = subid
                logging.info(f"{url} - Subscription ID: {subid}")
            else:
                logging.warning(
                    f"Failed to Subscribe {query} - Response: {response_dict}"
                )
    return query_to_subid


async def refresh_ws_subscriptions(base_url, cookie, query_to_subid):
    # Continuously refreshing the websocket subscriptions every 60 seconds.
    while True:
        await asyncio.sleep(60)
        for _, subid in query_to_subid.items():
            url = f"{base_url}/api/subscriptionRefresh.json?id={subid}"

            # Sending a GET request to refresh the subscriptions.
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, cookies=cookie, verify_ssl=False
                ) as refresh_resp:
                    # Logging the status of the refresh response.
                    # logging.info(f"Refresh response for subscription ID {subid} - Status Code: {refresh_resp.status}")
                    if refresh_resp.status != 200:
                        logging.warning(
                            f"Failed to refresh subscription ID {subid} - Response Message: {await refresh_resp.text()}"
                        )


async def get_audit_log(base_url, cookie, dn, status):
    change_sets = []
    descriptions = []
    users = []
    await asyncio.sleep(
        2
    )  # Delay 2 second for aaaModLR audit-log populated before processing
    # Constructing the URL to get the audit log for a specific DN.
    if status == "deleted":
        url = f'{base_url}/api/node/class/aaaModLR.json?query-target-filter=eq(aaaModLR.affected,"{dn}")&order-by=aaaModLR.created|desc&page=0&page-size=1'
    else:
        url = f"{base_url}/api/node/mo/{dn}.json?rsp-subtree-include=audit-logs,no-scoped,subtree&order-by=aaaModLR.created|desc&page=0&page-size=15"

    # Sending a GET request to get the audit log.
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, cookies=cookie, verify_ssl=False
            ) as audit_log_response:
                if audit_log_response.status == 200:
                    # Processing the audit log
                    audit_logs = await audit_log_response.json()
                    if not audit_logs["imdata"]:
                        return change_sets, descriptions, users
                    prev_timestamp = None
                    for log in audit_logs["imdata"]:
                        timestamp_str = log["aaaModLR"]["attributes"]["created"]
                        timestamp = datetime.strptime(
                            timestamp_str, "%Y-%m-%dT%H:%M:%S.%f%z"
                        )

                        if (
                            prev_timestamp
                            and abs((timestamp - prev_timestamp).total_seconds()) > 1
                        ):
                            break

                        prev_timestamp = timestamp

                        description = log["aaaModLR"]["attributes"].get("descr", "")
                        change_set = log["aaaModLR"]["attributes"].get("changeSet", "")
                        user = log["aaaModLR"]["attributes"].get("user", "")

                        if description and description not in descriptions:
                            descriptions.append(description)
                        if change_set and change_set not in change_sets:
                            change_sets.append(change_set)
                        if user and user not in users:
                            users.append(user)
                else:
                    logging.warning(
                        f"Failed to get audit log for {dn} - Status Code: {audit_log_response.status} - Response Message: {await audit_log_response.text()}"
                    )
    except Exception as e:
        logging.error(f"Process Audit Log Error: {e}")
    return change_sets, descriptions, users


async def print_mo_updates(ws, base_url, cookie, filter_mode, classes):
    # Continuously receiving and logging messages from the websocket connection.
    recent_updates = {}  # Cache recent updates
    scheduled_updates = set()  # Track which updates have been scheduled for processing

    async def process_update(dn):
        await asyncio.sleep(1)  # Buffer update for 1 second before processing
        final_update = recent_updates.pop(
            dn
        )  # Fetch and remove the update from the cache
        scheduled_updates.remove(dn)  # Remove dn from the set of scheduled updates

        status = next(iter(final_update.values())).get("attributes").get("status", "")
        change_sets, descriptions, users = await get_audit_log(
            base_url, cookie, dn, status
        )
        # Format the log message.
        padding = " " * (len(status) + 3 + 27)

        log_lines = [f'{status.capitalize()} - "dn":"{dn}"', f"{padding}{final_update}"]

        if descriptions:
            log_lines.append(f"{padding}Description: {descriptions[0]}")
            for desc in descriptions[1:]:
                log_lines.append(f"{padding}{' ' * len('Description: ')}{desc}")

        if change_sets:
            log_lines.append(f"{padding}Change Set: {change_sets[0]}")
            for cs in change_sets[1:]:
                log_lines.append(f"{padding}{' ' * len('Change Set: ')}{cs}")

        if users:
            log_lines.append(f"{padding}User: {users[0]}")
            for user in users[1:]:
                log_lines.append(f"{padding}{' ' * len('User: ')}{user}")

        log_message = "\n".join(log_lines)

        if filter_mode != "auto" or (filter_mode == "auto" and descriptions):
            logging.info(log_message)

    while True:
        try:
            message = await ws.recv()
            message_data = json.loads(message)
            for mo_data in message_data.get("imdata", []):
                # Extract the MO and its attributes.
                mo_class, attributes = next(iter(mo_data.items()))
                # Filtering based on mode
                if filter_mode == "whitelist" and mo_class not in classes:
                    continue
                elif filter_mode == "blacklist" and mo_class in classes:
                    continue
                else:  # No filtering for verbose mode
                    pass
                attributes = attributes.get("attributes", {})
                # Extract the 'dn' fields.
                dn = attributes.get("dn")

                # Merge new update with any recently buffered one
                if dn in recent_updates:
                    existing_data = recent_updates[dn]
                    existing_attrs = next(iter(existing_data.values())).get(
                        "attributes"
                    )
                    attributes_to_merge = attributes.copy()
                    attributes_to_merge.pop(
                        "status", None
                    )  # keep the status of the first update
                    existing_attrs.update(attributes_to_merge)  # add/update keys

                else:
                    recent_updates[dn] = mo_data

                # Schedule the processing of the update if not already scheduled
                if dn not in scheduled_updates:
                    scheduled_updates.add(dn)
                    asyncio.create_task(process_update(dn))

        except (websockets.ConnectionClosed, Exception) as e:
            logging.error(f"WebSocket Error: {e}")
            break


# --- Main & Signal Handling ---


async def main(config):
    # Constructing the base URL.
    base_url = f"https://{config['apic']}"

    # Getting the authentication cookie.
    cookie, refresh_timeout = await get_auth_cookie(
        config["username"], config["password"], base_url
    )

    # Opening the websocket connection.
    ws = await open_web_socket(config["apic"], cookie)

    # Subscribing to the queries and storing the subscription IDs.
    query_to_subid = await subscribe_to_queries(base_url, cookie, config["queries"])

    filter_mode = config.get("filter_mode")
    if filter_mode == "whitelist":
        classes = config.get("whitelisted_classes", [])
    elif filter_mode == "blacklist":
        classes = config.get("blacklisted_classes", [])
    else:  # for verbose mode
        classes = []

    # Creating tasks for printing messages, refreshing subscriptions, and refresh aaa Token.
    asyncio.create_task(print_mo_updates(ws, base_url, cookie, filter_mode, classes))
    asyncio.create_task(refresh_ws_subscriptions(base_url, cookie, query_to_subid))
    asyncio.create_task(
        refresh_cookie(
            config["username"], config["password"], base_url, cookie, refresh_timeout
        )
    )

    # Ensure the script run infinitely
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        # handle cleanup here
        pass


if __name__ == "__main__":
    print(
        "Logs are being written to 'apic-subscription.log'. Please monitor this file for updates."
    )

    # Loading configuration.
    config = asyncio.run(load_config("apic-subscription-config.yaml"))

    # Handling signals to shutdown gracefully.
    async def sig_handler(sig):
        logging.info(f"Received exit signal {sig.name}...")
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]
        logging.info(f"Cancelling {len(tasks)} tasks")
        await asyncio.gather(*tasks, return_exceptions=True)
        logging.info("Script has been shut down gracefully.")

    def handler(sig_num, frame):
        sig = signal.Signals(sig_num)
        asyncio.create_task(sig_handler(sig))

    for s in (signal.SIGTERM, signal.SIGINT):
        signal.signal(s, handler)

    # Running the main function.
    asyncio.run(main(config))
