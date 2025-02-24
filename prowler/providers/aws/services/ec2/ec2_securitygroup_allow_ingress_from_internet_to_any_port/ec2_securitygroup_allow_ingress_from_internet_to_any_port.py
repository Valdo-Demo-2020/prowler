from prowler.lib.check.models import Check, Check_Report_AWS
from prowler.providers.aws.services.ec2.ec2_client import ec2_client


class ec2_securitygroup_allow_ingress_from_internet_to_any_port(Check):
    def execute(self):
        findings = []
        for security_group in ec2_client.security_groups:
            report = Check_Report_AWS(self.metadata())
            report.region = security_group.region
            report.status = "PASS"
            report.status_extended = f"Security group {security_group.name} ({security_group.id}) has not all ports open to the Internet."
            report.resource_id = security_group.id
            report.resource_arn = security_group.arn
            report.resource_tags = security_group.tags
            if security_group.public_ports:
                report.status = "FAIL"
                report.status_extended = f"Security group {security_group.name} ({security_group.id}) has all ports open to the Internet."
            findings.append(report)

        return findings
