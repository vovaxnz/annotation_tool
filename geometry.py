import math


def find_line_equation(x, y, angle_degrees):
    # Calculate the slope (m) using the tangent of the angle
    if angle_degrees != 90:
        angle_radians = math.radians(angle_degrees)
        m = math.tan(angle_radians)
    else:
        m = 1e7
    # Calculate the y-intercept (b) using the point (xa, ya)
    b = y - m * x
    return m, b


def find_intersection(m1, b1, m2, b2):
    # Check if the lines are parallel (slopes are equal)
    if m1 == m2:
        return None  # No intersection (or infinite intersections if b1 == b2)
    # Calculate the x-coordinate of the intersection
    x = (b2 - b1) / (m1 - m2)
    # Calculate the y-coordinate of the intersection using either line equation
    y = m1 * x + b1
    return x, y


def line_length(x1, y1, x2, y2) -> float:
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def distort_point(x_undistorted, y_undistorted, mtx, dist, new_camera_mtx):
    """Returns distorted poinsts. Do the opposite operation than `undistort_point`"""
    # Convert undistorted point to normalized coordinates
    x_normalized = (x_undistorted - new_camera_mtx[0][2]) / new_camera_mtx[0][0]
    y_normalized = (y_undistorted - new_camera_mtx[1][2]) / new_camera_mtx[1][1]

    # Calculate r^2
    r2 = x_normalized**2 + y_normalized**2

    # Apply radial distortion
    x_radial = x_normalized * (1 + dist[0] * r2 + dist[1] * r2**2 + dist[4] * r2**3)
    y_radial = y_normalized * (1 + dist[0] * r2 + dist[1] * r2**2 + dist[4] * r2**3)

    # Apply tangential distortion
    x_tangential = 2 * dist[2] * x_normalized * y_normalized + dist[3] * (r2 + 2 * x_normalized**2)
    y_tangential = dist[2] * (r2 + 2 * y_normalized**2) + 2 * dist[3] * x_normalized * y_normalized

    x_distorted = x_radial + x_tangential
    y_distorted = y_radial + y_tangential

    # Convert back to pixel coordinates
    x_pixel = x_distorted * mtx[0][0] + mtx[0][2]
    y_pixel = y_distorted * mtx[1][1] + mtx[1][2]

    return x_pixel, y_pixel