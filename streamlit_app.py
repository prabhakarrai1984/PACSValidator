import streamlit as st
import xml.etree.ElementTree as ET
import xmlschema

# Preload schemas (adjust paths to where your XSDs are stored)
SCHEMAS = {
    "pacs.008": xmlschema.XMLSchema("C:/Users/prabh/Downloads/archive_business_area_payments_clearing_and_settlement_80b9af4a4c/pacs.008.001.13.xsd"),
    "pacs.009": xmlschema.XMLSchema("C:/Users/prabh/Downloads/archive_business_area_payments_clearing_and_settlement_80b9af4a4c/pacs.008.001.13.xsd")
}


def detect_message_type(message: str) -> str:
    """Detect message type from AppHdr/MsgDefIdr or Document root."""
    root = ET.fromstring(message)
    ns = {
        "env": "urn:swift:xsd:envelope",
        "head2": "urn:iso:std:iso:20022:tech:xsd:head.001.001.02",
        "head3": "urn:iso:std:iso:20022:tech:xsd:head.001.001.03"
    }
    msg_def = root.find(".//head2:MsgDefIdr", ns)
    if msg_def is None:
        msg_def = root.find(".//head3:MsgDefIdr", ns)
    if msg_def is not None:
        if "pacs.008" in msg_def.text:
            return "pacs.008"
        elif "pacs.009" in msg_def.text:
            return "pacs.009"

    # Fallback: check Document root
    for elem in root.iter():
        if elem.tag.endswith("Document") and elem.tag.startswith("{"):
            ns_uri = elem.tag.split("}")[0].strip("{")
            if "pacs.008" in ns_uri:
                return "pacs.008"
            elif "pacs.009" in ns_uri:
                return "pacs.009"
    return None

def normalize_namespace(message: str, msg_type: str) -> str:
    """
    Rewrite XML namespaces to match the latest schema version.
    Example: pacs.008.001.08 -> pacs.008.001.13
    """
    if msg_type == "pacs.008":
        latest_ns = "urn:iso:std:iso:20022:tech:xsd:pacs.008.001.13"
    elif msg_type == "pacs.009":
        latest_ns = "urn:iso:std:iso:20022:tech:xsd:pacs.009.001.09"
    else:
        return message

    # Replace any pacs.008.* or pacs.009.* namespace with latest
    import re
    message = re.sub(r"urn:iso:std:iso:20022:tech:xsd:pacs\.008\.\d+\.\d+", latest_ns, message)
    message = re.sub(r"urn:iso:std:iso:20022:tech:xsd:pacs\.009\.\d+\.\d+", latest_ns, message)
    return message

def validate_message(message: str):
    errors = []
    details = {}

    msg_type = detect_message_type(message)
    if not msg_type:
        errors.append("Unable to detect message type (MsgDefIdr missing).")
        return msg_type, details, errors

    schema = SCHEMAS.get(msg_type)
    if not schema:
        errors.append(f"No schema configured for {msg_type}.")
        return msg_type, details, errors

    # Normalize XML namespaces to latest version
    normalized_xml = normalize_namespace(message, msg_type)

    # Validate against latest schema
    if not schema.is_valid(normalized_xml):
        for e in schema.iter_errors(normalized_xml):
            errors.append(str(e))

    # Extract details
    try:
        root = ET.fromstring(normalized_xml)
        ns = {"pacs": schema.target_namespace}

        msg_id = root.find(".//pacs:MsgId", ns)
        if msg_id is not None:
            details["Message ID"] = msg_id.text

        amt = root.find(".//pacs:IntrBkSttlmAmt", ns)
        if amt is not None:
            details["Settlement Amount"] = amt.text + " " + amt.attrib.get("Ccy", "")

        dbtr = root.find(".//pacs:Dbtr/pacs:Nm", ns)
        if dbtr is not None:
            details["Debtor Name"] = dbtr.text

        cdtr = root.find(".//pacs:Cdtr/pacs:Nm", ns)
        if cdtr is not None:
            details["Creditor Name"] = cdtr.text
    except Exception as e:
        errors.append(f"Parsing error: {str(e)}")

    return msg_type, details, errors


# ---------------- Streamlit UI ----------------
st.title("ISO 20022 PACS Validator (Latest XSD, Backward-Compatible XML)")

message = st.text_area("Paste PACS XML message here (Only document):")

if st.button("Validate"):
    msg_type, details, errors = validate_message(message)

    if msg_type:
        st.write(f"Detected message type: **{msg_type}**")

    st.subheader("Extracted Details")
    if details:
        st.json(details)
    else:
        st.write("No details extracted.")

    st.subheader("Validation Errors")
    if errors:
        for err in errors:
            st.error(err)
    else:
        st.success("Message is valid against latest XSD ✅")
