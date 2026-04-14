from app.Integration.sap_api_client import SAPApiClient
class DashboardService:

    @staticmethod
    async def get_dashboard():

        ar_res = await SAPApiClient.get_open_ar_invoices()
        ap_res = await SAPApiClient.get_open_ap_invoices()
        in_res = await SAPApiClient.get_incoming_payments()
        out_res = await SAPApiClient.get_outgoing_payments()

        return {
            "total_open_ar_count": len(ar_res),
            "total_open_ap_count": len(ap_res),
            "total_incoming_payments": len(in_res),
            "total_outgoing_payments": len(out_res)
        }