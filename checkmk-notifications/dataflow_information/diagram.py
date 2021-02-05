from diagrams import Cluster, Diagram

from diagrams.gcp.compute import Functions

from diagrams.onprem.compute import Server
from diagrams.programming.language import Python

with Diagram("NS TCC Notifications", show=False):
    with Cluster("NS Infra"):
        server_1 = Server("Checkmk")
        script_1 = Python("Notifications_to_ODH.py")

        server_1 >> script_1

    with Cluster("GCP Operational Data Hub Platform"):
        with Cluster("vwt-p-gew1-ns-checkmk-int"):
            function_1 = Functions("Restingest")

    script_1 >> function_1
