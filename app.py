try:
    import os
    import sys
    import traceback
    from io import BytesIO

    import streamlit as st
    from pypdf import PaperSize, PdfReader, PdfWriter, Transformation
    from pypdf.errors import FileNotDecryptedError
    from streamlit import session_state
    from streamlit_pdf_viewer import pdf_viewer

    from utils import helpers, init_session_states, page_config, render_sidebar

    page_config.set()

    # ---------- HEADER ----------
    st.title("📄 PDF WorkDesk!")
    st.write(
        "User-friendly, lightweight, and open-source tool to preview and extract content and metadata from PDFs, add or remove passwords, modify, merge, convert and compress PDFs."
    )

    init_session_states.init()

    render_sidebar.render()

    # ---------- OPERATIONS ----------
    # TODO: Extract attachments (https://pypdf.readthedocs.io/en/stable/user/extract-attachments.html)
    # TODO: Undo last operation
    # TODO: Update metadata (https://pypdf.readthedocs.io/en/stable/user/metadata.html)

    try:
        (
            pdf,
            reader,
            session_state["password"],
            session_state["is_encrypted"],
        ) = helpers.load_pdf(key="main")

    except FileNotDecryptedError:
        pdf = "password_required"

    if pdf == "password_required":
        st.error("PDF is password protected. Please enter the password to proceed.")
    elif pdf:
        lcol, rcol = st.columns(2)
        with lcol.expander(label="🔍 Extract text"):
            extract_text_lcol, extract_text_rcol = st.columns(2)

            page_numbers_str = helpers.select_pages(
                container=extract_text_lcol,
                key="extract_text_pages",
            )

            mode = extract_text_rcol.radio(
                "Extraction mode",
                options=["plain", "layout"],
                horizontal=True,
                help="Layout mode extracts text in a format resembling the layout of the source PDF",
            )

            if page_numbers_str:
                try:
                    text = helpers.extract_text(reader, page_numbers_str, mode)
                except (IndexError, ValueError):
                    st.error("Specified pages don't exist. Check the format.", icon="⚠️")
                else:
                    st.text(text)

                    with open("text.txt", "w", encoding="utf-8") as f:
                        f.write(text)

                    with open("text.txt") as f:
                        st.download_button(
                            "💾 Download extracted text",
                            data=f,
                            use_container_width=True,
                        )

        with rcol.expander(label="️🖼️ Extract images"):
            if page_numbers_str := helpers.select_pages(
                container=st,
                key="extract_image_pages",
            ):
                try:
                    images = helpers.extract_images(reader, page_numbers_str)
                except (IndexError, ValueError):
                    st.error("Specified pages don't exist. Check the format.", icon="⚠️")
                else:
                    if images:
                        for data, name in images.items():
                            st.image(data, caption=name)
                    else:
                        st.info("No images found")

        with lcol.expander("📊 Extract table"):
            if page_numbers_str := helpers.select_pages(
                container=st,
                key="extract_table_pages",
            ):
                helpers.extract_tables(
                    session_state["file"],
                    page_numbers_str,
                )

        with rcol.expander("🔄️ Convert to Word"):
            st.caption("Takes ~1 second/page. Will remove password if present")

            if st.button("Convert PDF to Word", use_container_width=True):
                st.download_button(
                    "📥 Download Word document",
                    data=helpers.convert_pdf_to_word(pdf),
                    file_name=f"{session_state['name'][:-4]}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )

        with lcol.expander(
            f"🔐 {'Change' if session_state['is_encrypted'] else 'Add'} password"
        ):
            new_password = st.text_input(
                "Enter password",
                type="password",
            )

            algorithm = st.selectbox(
                "Algorithm",
                options=["RC4-40", "RC4-128", "AES-128", "AES-256-R5", "AES-256"],
                index=3,
                help="Use `RC4` for compatibility and `AES` for security",
            )

            filename = f"protected_{session_state['name']}"

            if st.button(
                "🔒 Submit",
                use_container_width=True,
                disabled=(len(new_password) == 0),
            ):
                with PdfWriter() as writer:
                    # Add all pages to the writer
                    for page in reader.pages:
                        writer.add_page(page)

                    # Add a password to the new PDF
                    writer.encrypt(new_password, algorithm=algorithm)

                    # Save the new PDF to a file
                    with open(filename, "wb") as f:
                        writer.write(f)

            if os.path.exists(filename):
                st.download_button(
                    "📥 Download protected PDF",
                    data=open(filename, "rb"),
                    mime="application/pdf",
                    file_name=filename,
                    use_container_width=True,
                )

        with rcol.expander("🔓 Remove password"):
            if reader.is_encrypted:
                st.download_button(
                    "📥 Download unprotected PDF",
                    data=open(session_state["decrypted_filename"], "rb"),
                    mime="application/pdf",
                    file_name=session_state["decrypted_filename"],
                    use_container_width=True,
                )
            else:
                st.info("PDF does not have a password")

        with lcol.expander("🔃 Rotate PDF"):
            # TODO: Add password back to converted PDF if original was protected
            st.caption("Will remove password if present")
            angle = st.slider(
                "Clockwise angle",
                min_value=0,
                max_value=270,
                step=90,
                format="%d°",
            )

            with PdfWriter() as writer:
                for page in reader.pages:
                    writer.add_page(page)
                    writer.pages[-1].rotate(angle)

                # TODO: Write to byte_stream
                writer.write("rotated.pdf")

                with open("rotated.pdf", "rb") as f:
                    pdf_viewer(f.read(), height=250, width=300)
                    st.download_button(
                        "📥 Download rotated PDF",
                        data=f,
                        mime="application/pdf",
                        file_name=f"{session_state['name'].rsplit('.')[0]}_rotated_{angle}.pdf",
                        use_container_width=True,
                    )

        with rcol.expander("↔ Resize/Scale PDF"):
            # TODO: Add password back to converted PDF if original was protected
            st.caption("Will remove password if present")
            new_size = st.selectbox(
                "New size",
                options={
                    attr: getattr(PaperSize, attr)
                    for attr in dir(PaperSize)
                    if not attr.startswith("__")
                    and not callable(getattr(PaperSize, attr))
                },
                index=4,
                help="Changes will be apparant only on printing the PDF",
            )

            scale_content = st.slider(
                "Scale content",
                min_value=0.1,
                max_value=2.0,
                step=0.1,
                value=1.0,
                help="Scale content independently of the page size",
                format="%fx",
            )

            with PdfWriter() as writer:
                for page in reader.pages:
                    page.scale_to(
                        width=getattr(PaperSize, new_size).width,
                        height=getattr(PaperSize, new_size).height,
                    )
                    op = Transformation().scale(sx=scale_content, sy=scale_content)
                    page.add_transformation(op)
                    writer.add_page(page)

                # TODO: Write to byte_stream
                writer.write("scaled.pdf")

                with open("scaled.pdf", "rb") as f:
                    st.caption("Content scaling preview")
                    pdf_viewer(f.read(), height=250, width=300)
                    st.download_button(
                        "📥 Download scaled PDF",
                        data=f,
                        mime="application/pdf",
                        file_name=f"{session_state['name'].rsplit('.')[0]}_scaled_{new_size}_{scale_content}x.pdf",
                        use_container_width=True,
                    )

        # with st.expander("©️ Add watermark"):
        # TODO: Add watermark (convert pdf to image and then back to pdf with watermark)
        #     # TODO: Transform watermark before adding (https://pypdf.readthedocs.io/en/stable/user/add-watermark.html#stamp-overlay-watermark-underlay)

        #     col1, col2 = st.columns(2)

        #     image = col1.file_uploader(
        #         "Upload image",
        #         type=["png", "jpg", "jpeg", "webp", "bmp"],
        #     )

        #     if image:
        #         col2.image(image, caption="Uploaded image", use_column_width=True)

        #         utils.watermark_img(
        #             reader,
        #             image,
        #         )

        #         pdf_viewer("watermarked.pdf", height=400, width=500)

        #         st.download_button(
        #             "📥 Download watermarked PDF",
        #             data=open("watermarked.pdf", "rb"),
        #             mime="application/pdf",
        #             file_name="watermarked.pdf",
        #             use_container_width=True,
        #         )

        with lcol.expander("➕ Merge PDFs"):
            # TODO: Add password back to converted PDF if original was protected
            st.caption(
                "Second PDF will be appended to the first. Passwords will be removed from both."
            )
            # TODO: Add more merge options (https://pypdf.readthedocs.io/en/stable/user/merging-pdfs.html#showing-more-merging-options)
            pdf_to_merge, reader_to_merge, *_ = helpers.load_pdf(key="merge")

            if st.button(
                "➕ Merge PDFs", disabled=(not pdf_to_merge), use_container_width=True
            ):
                with PdfWriter() as merger:
                    for file in (reader, reader_to_merge):
                        merger.append(file)

                    # TODO: Write to byte_stream
                    merger.write("merged.pdf")

                    pdf_viewer(
                        open("merged.pdf", "rb").read(),
                        height=250,
                        width=300,
                    )
                    st.download_button(
                        "📥 Download merged PDF",
                        data=open("merged.pdf", "rb"),
                        mime="application/pdf",
                        file_name="merged.pdf",
                        use_container_width=True,
                    )

        with st.expander("🤏 Reduce PDF size"):
            # TODO: Add password back to converted PDF if original was protected
            st.caption("Will remove password if present")

            pdf_small = pdf

            lcol, mcol, rcol = st.columns(3)

            with lcol:
                remove_duplication = st.checkbox(
                    "Remove duplication",
                    help="""
                    Some PDF documents contain the same object multiple times.  
                    For example, if an image appears three times in a PDF it could be embedded three times. 
                    Or it can be embedded once and referenced twice.  
                    **Note:** This option will not remove objects, rather it will use a reference to the original object for subsequent uses.
                    """,
                )

                remove_images = st.checkbox(
                    "Remove images",
                    help="Remove images from the PDF. Will also remove duplication.",
                )

                if remove_images or remove_duplication:
                    pdf_small = helpers.remove_images(
                        pdf,
                        remove_images=remove_images,
                        password=session_state.password,
                    )

                if st.checkbox(
                    "Reduce image quality",
                    help="""
                    Reduce the quality of images in the PDF. Will also remove duplication.  
                    May not work for all cases.
                    """,
                    disabled=remove_images,
                ):
                    quality = st.slider(
                        "Quality",
                        min_value=0,
                        max_value=100,
                        value=50,
                        disabled=remove_images,
                    )
                    pdf_small = helpers.reduce_image_quality(
                        pdf_small,
                        quality,
                        password=session_state.password,
                    )

                if st.checkbox(
                    "Lossless compression",
                    help="Compress PDF without losing quality",
                ):
                    pdf_small = helpers.compress_pdf(
                        pdf_small, password=session_state.password
                    )

                original_size = sys.getsizeof(pdf)
                reduced_size = sys.getsizeof(pdf_small)
                st.caption(
                    f"Reduction: {100 - (reduced_size / original_size) * 100:.2f}%"
                )

            with mcol:
                st.caption(f"Original size: {original_size / 1024:.2f} KB")
                helpers.preview_pdf(
                    reader,
                    pdf,
                    key="other",
                    password=session_state.password,
                )
            with rcol:
                st.caption(f"Reduced size: {reduced_size / 1024:.2f} KB")
                helpers.preview_pdf(
                    PdfReader(BytesIO(pdf_small)),
                    pdf_small,
                    key="other",
                    password=session_state.password,
                )
            st.download_button(
                "📥 Download smaller PDF",
                data=pdf_small,
                mime="application/pdf",
                file_name=f"{filename}_reduced.pdf",
                use_container_width=True,
            )

except Exception as e:
    st.error(
        f"""The app has encountered an error:  
        `{e}`  
        Please create an issue [here](https://github.com/SiddhantSadangi/pdf-workdesk/issues/new) 
        with the below traceback""",
        icon="🥺",
    )
    st.code(traceback.format_exc())

st.success(
    "[Star the repo](https://github.com/SiddhantSadangi/pdf-workdesk) to show your :heart:",
    icon="⭐",
)
