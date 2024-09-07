from typing import List, Optional, Dict, Any
import logging
import os
import json
import glob

from fastapi import FastAPI, HTTPException, Header, Response, Body, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.encoders import jsonable_encoder

from skiff.app.api.app.metadata import PaperStatus, Allocation
from skiff.app.api.app.annotations import Annotation, RelationGroup, PdfAnnotation, Bounds, Label, TokenId
from skiff.app.api.app.utils import StackdriverJsonFormatter
from skiff.app.api.app import pre_serve

import papermage
from papermage.recipes import CoreRecipe
from papermage.magelib import Document, Box, Entity, Span
import shutil

IN_PRODUCTION = os.getenv("IN_PRODUCTION", "dev")

CONFIGURATION_FILE = os.getenv(
    "PAWLS_CONFIGURATION_FILE", "/usr/local/src/skiff/app/api/config/configuration.json"
)

handlers = None

if IN_PRODUCTION == "prod":
    json_handler = logging.StreamHandler()
    json_handler.setFormatter(StackdriverJsonFormatter())
    handlers = [json_handler]

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", default=logging.INFO), handlers=handlers
)
logger = logging.getLogger("uvicorn")

# boto3 logging is _super_ verbose.
logging.getLogger("boto3").setLevel(logging.CRITICAL)
logging.getLogger("botocore").setLevel(logging.CRITICAL)
logging.getLogger("nose").setLevel(logging.CRITICAL)
logging.getLogger("s3transfer").setLevel(logging.CRITICAL)

# The annotation app requires a bit of set up.
configuration = pre_serve.load_configuration(CONFIGURATION_FILE)

app = FastAPI()

def get_user_from_header(user_email: Optional[str]) -> Optional[str]:
    """
    Call this function with the X-Auth-Request-Email header value. This must
    include an "@" in its value.

    * In production, this is provided by Skiff after the user authenticates.
    * In development, it is provided in the NGINX proxy configuration file local.conf.

    If the value isn't well formed, or the user isn't allowed, an exception is
    thrown.
    """
    if user_email is None:
        return "development_user@example.com"
    
    if "@" not in user_email:
        raise HTTPException(403, "Forbidden")

    if not user_is_allowed(user_email):
        raise HTTPException(403, "Forbidden")

    return user_email


def user_is_allowed(user_email: str) -> bool:
    """
    Return True if the user_email is in the users file, False otherwise.
    """
    try:
        with open(configuration.users_file) as file:
            for line in file:
                entry = line.strip()
                if user_email == entry:
                    return True
                # entries like "@allenai.org" mean anyone in that domain @allenai.org is granted access
                if entry.startswith("@") and user_email.endswith(entry):
                    return True
    except FileNotFoundError:
        logger.warning("file not found: %s", configuration.users_file)
        pass

    return False


def all_pdf_shas() -> List[str]:
    pdfs = glob.glob(f"{configuration.output_directory}/*/*.pdf")
    return [p.split("/")[-2] for p in pdfs]


@app.post("/api/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        # Save the uploaded file
        file_location = f"{configuration.output_directory}/{file.filename}"
        with open(file_location, "wb+") as file_object:
            file_object.write(file.file.read())

        # Process the PDF using core_recipe
        document = Document(file_location)
        core_recipe = CoreRecipe()
        from pdf2image import convert_from_path
        import os

        # Set the poppler path
        os.environ["PATH"] += os.pathsep + "/openhands/miniforge3/envs/poppler_env/bin"

        # Process the PDF using core_recipe
        document = core_recipe.from_pdf(file_location)

        # Store the output of the to_json method
        json_output = document.to_json()
        sha = file.filename.split('.')[0]
        json_output_location = f"{configuration.output_directory}/{sha}/{sha}.json"
        pdf_output_location = f"{configuration.output_directory}/{sha}/{sha}.pdf"
        os.makedirs(os.path.dirname(json_output_location), exist_ok=True)
        shutil.copy(file_location, pdf_output_location) 
        os.makedirs(os.path.dirname(json_output_location), exist_ok=True) 
        with open(json_output_location, "w") as json_file:
            json.dump(json_output, json_file)

        return {"filename": file.filename, "status": "success"}
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        raise HTTPException(status_code=500, detail="Error processing PDF")
    
# @app.get("/api/doc/{sha}/pdf")
# async def get_pdf(sha: str):
#     """
#     Fetches a PDF.

#     sha: str
#         The sha of the pdf to return.
#     """
#     json_path = os.path.join(configuration.output_directory, sha, f"{sha}.json")
#     if not os.path.exists(json_path):
#         raise HTTPException(status_code=404, detail="PDF not found")
    
#     with open(json_path, "r") as f:
#         doc_json = json.load(f)
    
#     doc = Document.from_json(doc_json)
    
#     # Extract necessary data from Document
#     pdf_data = {
#         "symbols": doc.symbols,
#         "metadata": doc.metadata.to_dict() if doc.metadata else {}, 
#         "pages": [page.__dict__ for page in doc.pages.entities], 
#     }
    
#     return pdf_data

@app.get("/api/doc/{sha}/pdf")
async def get_pdf(sha: str):
    """
    Fetches a PDF.

    sha: str
        The sha of the pdf to return.
    """
    pdf = os.path.join(configuration.output_directory, sha, f"{sha}.pdf")
    pdf_exists = os.path.exists(pdf)
    if not pdf_exists:
        raise HTTPException(status_code=404, detail=f"pdf {sha} not found.")

    return FileResponse(pdf, media_type="application/pdf")


    
    with open(f"{output_dir}/pdf_structure.json", "w") as f:
        json.dump(doc_json, f)
    
    with open(f"{output_dir}/{file.filename.split('.')[0]}.json", "w") as f:
        json.dump(doc_json, f)
    
    return {"sha": file.filename.split('.')[0]}
    
    return {"filename": file.filename, "message": "PDF processed and saved successfully"}

@app.get("/api/doc/{sha}/title")
async def get_pdf_title(sha: str) -> Optional[str]:
    """
    Fetches a PDF's title.

    sha: str
        The sha of the pdf title to return.
    """
    pdf_info = os.path.join(configuration.output_directory, "pdf_metadata.json")

    with open(pdf_info, "r") as f:
        info = json.load(f)

    data = info.get("sha", None)

    if data is None:
        return None

    return data.get("title", None)

@app.post("/api/doc/{sha}/comments")
def set_pdf_comments(
    sha: str, comments: str = Body(...), x_auth_request_email: str = Header(None)
):
    user = get_user_from_header(x_auth_request_email)
    status_path = os.path.join(configuration.output_directory, "status", f"{user}.json")
    exists = os.path.exists(status_path)

    if not exists:
        # Not an allocated user. Do nothing.
        return {}

    update_status_json(status_path, sha, {"comments": comments})
    return {}

@app.post("/api/doc/{sha}/junk")
def set_pdf_junk(
    sha: str, junk: bool = Body(...), x_auth_request_email: str = Header(None)
):
    user = get_user_from_header(x_auth_request_email)
    status_path = os.path.join(configuration.output_directory, "status", f"{user}.json")
    exists = os.path.exists(status_path)
    if not exists:
        # Not an allocated user. Do nothing.
        return {}

    update_status_json(status_path, sha, {"junk": junk})
    return {}

def update_status_json(status_path: str, sha: str, data: Dict[str, Any]):

    with open(status_path, "r+") as st:
        status_json = json.load(st)
        status_json[sha] = {**status_json[sha], **data}
        st.seek(0)
        json.dump(status_json, st)
        st.truncate()


@app.get("/", status_code=204)
def read_root():
    """
    Skiff's sonar, and the Kubernetes health check, require
    that the server returns a 2XX response from it's
    root URL, so it can tell the service is ready for requests.
    """
    return Response(status_code=204)

@app.get("/api/doc/{sha}/annotations")
async def get_annotations(sha: str):
    """
    Fetches annotations for a PDF.

    sha: str
        The sha of the pdf to return annotations for.
    """
    json_path = os.path.join(configuration.output_directory, sha, f"{sha}.json")
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="PDF not found")
    
    with open(json_path, "r") as f:
        doc_json = json.load(f)
    
    doc = Document.from_json(doc_json)
    
    # Extract annotations from Document
    annotations = [
        Annotation(
            id=entity.id,
            page=entity.page,
            label=Label(text=entity.label, color=""),
            bounds=Bounds(left=entity.bounds.left, top=entity.bounds.top, right=entity.bounds.right, bottom=entity.bounds.bottom),
            tokens=[TokenId(pageIndex=token.page_index, tokenIndex=token.token_index) for token in entity.tokens]
        )
        for entity in doc.entities
    ]
    
    return annotations

@app.post("/api/doc/{sha}/annotations")
async def post_annotations(
    sha: str,
    annotations: List[Annotation],
    user_email: Optional[str] = Header(None),
):
    user = get_user_from_header(user_email)
    json_path = os.path.join(configuration.output_directory, sha, f"{sha}.json")
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="PDF not found")
    
    with open(json_path, "r") as f:
        doc_json = json.load(f)
    
    doc = Document.from_json(doc_json)
    
    # Convert annotations to Document format
    entities = [
        Entity(
            id=annotation.id,
            page=annotation.page,
            label=annotation.label.text,
            bounds=Box(left=annotation.bounds.left, top=annotation.bounds.top, right=annotation.bounds.right, bottom=annotation.bounds.bottom),
            tokens=[Span(page_index=token.pageIndex, token_index=token.tokenIndex) for token in annotation.tokens]
        )
        for annotation in annotations
    ]
    doc.annotate_layer(name="annotations", entities=entities)
    
    # Save updated Document
    doc_json = doc.to_json()
    with open(json_path, "w") as f:
        json.dump(doc_json, f)
    
    return annotations

@app.get("/api/doc/{sha}/tokens")
async def get_tokens(sha: str):
    """
    Fetches tokens for a PDF.

    sha: str
        The sha of the pdf to return tokens for.
    """
    json_path = os.path.join(configuration.output_directory, sha, f"{sha}.json")
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="PDF not found")
    
    with open(json_path, "r") as f:
        doc_json = json.load(f)
    
    doc = Document.from_json(doc_json)
    
    # Extract tokens from Document
    tokens = [
        {
            "pageIndex": token.page_index,
            "tokenIndex": token.token_index,
            "text": token.text,
            "bounds": {
                "left": token.bounds.left,
                "top": token.bounds.top,
                "right": token.bounds.right,
                "bottom": token.bounds.bottom
            }
        }
        for token in doc.tokens
    ]
    
    return tokens

@app.get("/api/annotation/labels")
async def get_labels():
    """
    Fetches annotation labels.
    """
    json_path = os.path.join(configuration.output_directory, "sample", "sample.json")
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Labels not found")
    
    with open(json_path, "r") as f:
        doc_json = json.load(f)
    
    doc = Document.from_json(doc_json)
    labels = doc.metadata.labels
    return labels

@app.get("/api/annotation/relations")
async def get_relations():
    """
    Fetches annotation relations.
    """
    json_path = os.path.join(configuration.output_directory, "sample", "sample.json")
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Relations not found")
    
    with open(json_path, "r") as f:
        doc_json = json.load(f)
    
    doc = Document.from_json(doc_json)
    relations = doc.metadata.relations
    return relations

@app.get("/api/annotation/allocation/info")
def get_allocation_info(x_auth_request_email: str = Header(None)) -> Allocation:

    # In development, the app isn't passed the x_auth_request_email header,
    # meaning this would always fail. Instead, to smooth local development,
    # we always return all pdfs, essentially short-circuiting the allocation
    # mechanism.
    user = get_user_from_header(x_auth_request_email)

    status_dir = os.path.join(configuration.output_directory, "status")
    status_path = os.path.join(status_dir, f"{user}.json")
    exists = os.path.exists(status_path)

    if not exists:
        # If the user doesn't have allocated papers, they can see all the
        # pdfs but they can't save anything.
        papers = [PaperStatus.empty(sha, sha) for sha in all_pdf_shas()]
        response = Allocation(
            papers=papers,
            hasAllocatedPapers=False
        )

    else:
        with open(status_path) as f:
            status_json = json.load(f)

        papers = []
        for sha, status in status_json.items():
            papers.append(PaperStatus(**status))

        response = Allocation(papers=papers, hasAllocatedPapers=True)

    return response

