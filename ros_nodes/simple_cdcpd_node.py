import rospy
from sensor_msgs.msg import PointCloud2
import numpy as np
from numpy.lib.recfunctions import structured_to_unstructured, unstructured_to_structured
import ros_numpy
from cdcpd.cdcpd import CDCPDParams, ConstrainedDeformableCPD
from cdcpd.cpd import CPDParams
from cdcpd.optimizer import DistanceConstrainedOptimizer
from cdcpd.geometry_utils import build_line
from cdcpd.cv_utils import chroma_key_rope
from cdcpd.prior import ThresholdVisibilityPrior


kinect_intrinsics = np.array(
    [1068.842896477257, 0.0, 950.2974736758024, 0.0, 1066.0150152835104, 537.097974092338, 0.0, 0.0, 1.0],
    dtype=np.float32).reshape((3, 3))
kinect_intrinsics[:2] /= 2.0

template_verts, template_edges = build_line(1.0, 50)
key_func = chroma_key_rope

prior = ThresholdVisibilityPrior(kinect_intrinsics)
optimizer = DistanceConstrainedOptimizer(template=template_verts, edges=template_edges)

cpd_params = CPDParams(beta=4.0)
cdcpd_params = CDCPDParams(prior=prior, optimizer=optimizer, down_sample_size=150)
cdcpd = ConstrainedDeformableCPD(template=template_verts,
                                 cdcpd_params=cdcpd_params)

pub = rospy.Publisher("/cdcpd_tracker/points", PointCloud2, queue_size=10)


def callback(msg: PointCloud2):
    data = ros_numpy.numpify(msg)
    arr = ros_numpy.point_cloud2.split_rgb_field(data)
    point_cloud_img = structured_to_unstructured(arr[['x', 'y', 'z']])
    color_img = structured_to_unstructured(arr[['r', 'g', 'b']])
    mask_img = key_func(point_cloud_img, color_img)

    tracking_result = cdcpd.step(point_cloud=point_cloud_img,
                                 mask=mask_img,
                                 cpd_param=cpd_params)

    out_struct_arr = unstructured_to_structured(tracking_result, names=['x', 'y', 'z'])
    pub_msg = ros_numpy.msgify(PointCloud2, out_struct_arr)
    pub_msg.header = msg.header
    pub.publish(pub_msg)


def main():
    rospy.init_node('cdcpd_tracker_node')
    rospy.Subscriber("/kinect2_victor_head/qhd/points", PointCloud2, callback, queue_size=1)

    rospy.spin()


main()

