"""Adapter to convert a PIR object to a ProcessModel for simulation."""
from ..pir import PIR
from .core import ProcessModel, State

def pir_to_process_model(pir: PIR) -> ProcessModel:
    """Converts a Process Intermediate Representation (PIR) object to a ProcessModel."""
    p = ProcessModel(pir.metadata.get("name", "process"))
    with p:
        # Create states from PIR nodes and store them, mapping node ID to State object
        created_states = {node.id: State(node.name) for node in pir.nodes.values()}

        # Create transitions from PIR edges
        for edge in pir.edges:
            src_state = created_states.get(edge.src)
            dst_state = created_states.get(edge.dst)
            if src_state and dst_state:
                # Assuming a probability of 1.0 for now
                p.add_transition(src_state >> 1.0 >> dst_state)
    return p
