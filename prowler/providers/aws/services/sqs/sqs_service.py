import threading
from json import loads
from typing import Optional

from pydantic import BaseModel

from prowler.lib.logger import logger
from prowler.lib.scan_filters.scan_filters import is_resource_filtered
from prowler.providers.aws.aws_provider import generate_regional_clients


################################ SQS
class SQS:
    def __init__(self, audit_info):
        self.service = "sqs"
        self.session = audit_info.audit_session
        self.audit_resources = audit_info.audit_resources
        self.audited_account = audit_info.audited_account
        self.audited_partition = audit_info.audited_partition
        self.regional_clients = generate_regional_clients(self.service, audit_info)
        self.queues = []
        self.__threading_call__(self.__list_queues__)
        self.__get_queue_attributes__(self.regional_clients)
        self.__list_queue_tags__()

    def __get_session__(self):
        return self.session

    def __threading_call__(self, call):
        threads = []
        for regional_client in self.regional_clients.values():
            threads.append(threading.Thread(target=call, args=(regional_client,)))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def __list_queues__(self, regional_client):
        logger.info("SQS - describing queues...")
        try:
            list_queues_paginator = regional_client.get_paginator("list_queues")
            for page in list_queues_paginator.paginate():
                if "QueueUrls" in page:
                    for queue in page["QueueUrls"]:
                        arn = f"arn:{self.audited_partition}:sqs:{regional_client.region}:{self.audited_account}:{queue}"
                        if not self.audit_resources or (
                            is_resource_filtered(arn, self.audit_resources)
                        ):
                            self.queues.append(
                                Queue(
                                    arn=arn,
                                    id=queue,
                                    region=regional_client.region,
                                )
                            )
        except Exception as error:
            logger.error(
                f"{regional_client.region} -- {error.__class__.__name__}[{error.__traceback__.tb_lineno}]: {error}"
            )

    def __get_queue_attributes__(self, regional_clients):
        try:
            logger.info("SQS - describing queue attributes...")
            for queue in self.queues:
                regional_client = regional_clients[queue.region]
                queue_attributes = regional_client.get_queue_attributes(
                    QueueUrl=queue.id, AttributeNames=["All"]
                )
                if "Attributes" in queue_attributes:
                    if "Policy" in queue_attributes["Attributes"]:
                        queue.policy = loads(queue_attributes["Attributes"]["Policy"])
                    if "KmsMasterKeyId" in queue_attributes["Attributes"]:
                        queue.kms_key_id = queue_attributes["Attributes"][
                            "KmsMasterKeyId"
                        ]
                    if "SqsManagedSseEnabled" in queue_attributes["Attributes"]:
                        if (
                            queue_attributes["Attributes"]["SqsManagedSseEnabled"]
                            == "true"
                        ):
                            queue.kms_key_id = "SqsManagedSseEnabled"

        except Exception as error:
            logger.error(
                f"{regional_client.region} -- {error.__class__.__name__}[{error.__traceback__.tb_lineno}]: {error}"
            )

    def __list_queue_tags__(self):
        logger.info("SQS - List Tags...")
        try:
            for queue in self.queues:
                regional_client = self.regional_clients[queue.region]
                response = regional_client.list_queue_tags(QueueUrl=queue.id).get(
                    "Tags"
                )
                queue.tags = [response]
        except Exception as error:
            logger.error(
                f"{regional_client.region} -- {error.__class__.__name__}[{error.__traceback__.tb_lineno}]: {error}"
            )


class Queue(BaseModel):
    id: str
    arn: str
    region: str
    policy: dict = None
    kms_key_id: str = None
    tags: Optional[list] = []
