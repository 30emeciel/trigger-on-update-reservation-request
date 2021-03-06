import logging
import os

import firebase_admin
from box import Box
from firebase_admin import credentials
from firebase_admin import firestore
# Use the application default credentials
from jinja2 import Environment, FileSystemLoader, select_autoescape
from box import Box
from mail import send_mail
from rst import generate_confirmed_reservation_html_text, generate_confirmed_reservation_title

cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred, {
    'projectId': "trentiemeciel",
})

logging.basicConfig(level=os.environ.get("LOGGING_LEVEL", "DEBUG"))

log = logging.getLogger(__name__)
db = firestore.client()

env = Environment(
    loader=FileSystemLoader("res"),
    autoescape=select_autoescape(['html', 'xml'])
)


def from_firestore(event, context):
    """Triggered by a change to a Firestore document.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    resource_string = context.resource

    # print out the resource string that triggered the function
    log.info(f"Function triggered by change to: {resource_string}.")
    # now print out the entire event object
    log.debug(str(event))

    trigger_on_update_reservation_request(resource_string, Box(event))


def trigger_on_update_reservation_request(doc_path, event):

    if "state" not in event.updateMask.fieldPaths:
        log.info("state hasn't changed, ignoring")
        return

    request_ref = db.document(doc_path)
    pax_ref = request_ref.parent.parent
    pax_doc, request_doc = pax_ref.get(), request_ref.get()
    assert pax_doc.exists and request_doc.exists

    request_plus_id = request_doc.to_dict()
    request_plus_id.update({"id": request_doc.id})
    request = Box(request_plus_id)
    pax = Box(pax_doc.to_dict())
    if request.state != "CONFIRMED":
        log.info(f"request 'state' != CONFIRMED, ignoring")
        return

    html = generate_confirmed_reservation_html_text(pax, request)
    title = generate_confirmed_reservation_title(pax, request)

    send_mail(pax.email, title, html)

