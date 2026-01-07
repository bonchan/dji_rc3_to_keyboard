def map_drone(item):
    if not item:
        return None
    
    host = item.get("host", {})
    parents = map_docks(item.get("parents", []))
    state = host.get("device_state", {})
    
    # Initialize variables with None/Defaults to prevent crashes
    gimbal_pitch = gimbal_yaw = None
    target_lat = target_lon = None

    # Safe extraction of camera/payload data
    cameras = state.get("cameras", [])
    if cameras: # Pythonic way to check if list is not empty
        payload_index = cameras[0].get("payload_index")
        payload = state.get(payload_index, {}) # Use {} as default to avoid None.get()
        
        gimbal_pitch = payload.get("gimbal_pitch")
        gimbal_yaw = payload.get("gimbal_yaw")
        target_lat = payload.get("measure_target_latitude")
        target_lon = payload.get("measure_target_longitude")

    return {
        "device_sn": host.get("device_sn"),
        "longitude": state.get("longitude"),
        "latitude": state.get("latitude"),
        "elevation": state.get("elevation"),
        "yaw": state.get("attitude_head"),
        "gimbal_pitch": gimbal_pitch,
        "gimbal_yaw": gimbal_yaw,
        "measure_target_longitude": target_lon,
        "measure_target_latitude": target_lat,
        "parents": parents,
    }

def map_docks(parents):
    if not parents:
        return None
    return [map_dock(parent) for parent in parents]

def map_dock(parent):
    if not parent:
        return None
    
    state = parent.get("device_state", {})
    
    return {
        "device_sn": parent.get("device_sn"),
        "device_organization_callsign": parent.get("device_organization_callsign"),
        "drone_in_dock": state.get("drone_in_dock"),
        "longitude": state.get("longitude"),
        "latitude": state.get("latitude"),
    }

def map_topologies(data, target_sn=None, has_parents=True):
    """
    If target_sn is provided, returns a single dict or None.
    If target_sn is None, returns a list of all drones.
    """
    drone_list = data.get("data", {}).get("list", [])

    if has_parents:
        drone_list = [item for item in drone_list if item.get("parents")]

    if target_sn:
        # Find the specific drone
        # Added a check: only drones with "parents" (usually means active in topology)
        target_item = next(
            (item for item in drone_list if item.get("host", {}).get("device_sn") == target_sn), 
            None
        )
        return map_drone(target_item)
    
    # Otherwise, map the whole list
    return [map_drone(item) for item in drone_list]