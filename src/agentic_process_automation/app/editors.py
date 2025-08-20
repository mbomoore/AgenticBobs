"""BPMN and DMN editors integration for Streamlit.

Provides embedded bpmn.io and dmn.io editors within Streamlit applications.
"""
import streamlit as st
import streamlit.components.v1 as components


def bpmn_editor(xml_content: str = "", height: int = 600, key: str = None) -> str:
    """Embed a BPMN editor using bpmn.io.
    
    Args:
        xml_content: Initial BPMN XML content
        height: Height of the editor in pixels
        key: Unique key for the component
        
    Returns:
        Updated BPMN XML content from the editor
    """
    # For now, provide a simple text area as a placeholder
    # TODO: Implement actual bpmn.io integration
    st.info("BPMN Editor (placeholder - bpmn.io integration pending)")
    
    updated_xml = st.text_area(
        "BPMN XML Content",
        value=xml_content,
        height=height // 10,  # Approximate height conversion
        key=key
    )
    
    return updated_xml


def dmn_editor(xml_content: str = "", height: int = 600, key: str = None) -> str:
    """Embed a DMN editor using dmn.io.
    
    Args:
        xml_content: Initial DMN XML content
        height: Height of the editor in pixels
        key: Unique key for the component
        
    Returns:
        Updated DMN XML content from the editor
    """
    # For now, provide a simple text area as a placeholder
    # TODO: Implement actual dmn.io integration
    st.info("DMN Editor (placeholder - dmn.io integration pending)")
    
    updated_xml = st.text_area(
        "DMN XML Content",
        value=xml_content,
        height=height // 10,  # Approximate height conversion
        key=key
    )
    
    return updated_xml


def sanity_check_component(key: str = None) -> bool:
    """Simple sanity check component to verify Streamlit custom components work.
    
    Args:
        key: Unique key for the component
        
    Returns:
        True if button was clicked
    """
    st.info("Sanity Check Component")
    
    # Use built-in Streamlit button as fallback
    clicked = st.button("Test Component", key=key)
    
    if clicked:
        st.success("Component working! ✅")
        st.write(f"Timestamp: {st.timestamp}")
    
    return clicked


# Placeholder for future bpmn.io/dmn.io JavaScript integration
_BPMN_IO_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>BPMN Editor</title>
    <script src="https://unpkg.com/bpmn-js@latest/dist/bpmn-modeler.development.js"></script>
</head>
<body>
    <div id="canvas" style="height: {height}px;"></div>
    <script>
        // TODO: Implement bpmn.io integration
        var modeler = new BpmnJS({{
            container: '#canvas'
        }});
        
        var xml = `{xml_content}`;
        modeler.importXML(xml, function(err) {{
            if (err) {{
                console.error('Error importing XML:', err);
            }}
        }});
    </script>
</body>
</html>
"""