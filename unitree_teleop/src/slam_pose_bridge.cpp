#include <chrono>
#include <memory>
#include <string>

#include <gz/msgs/pose_v.pb.h>
#include <gz/transport/Node.hh>

#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/transform_stamped.hpp>
#include <tf2_ros/transform_broadcaster.h>

class SlamPoseBridge : public rclcpp::Node
{
public:
  SlamPoseBridge()
  : Node("slam_pose_bridge")
  {
    broadcaster_ =
      std::make_unique<tf2_ros::TransformBroadcaster>(*this);

    if (!gz_node_.Subscribe(
        "/world/go2_world/dynamic_pose/info",
        &SlamPoseBridge::poseCallback, this))
    {
      RCLCPP_ERROR(
        get_logger(), "Gazebo-Topic konnte nicht abonniert werden.");
    }
    else
    {
      RCLCPP_INFO(
        get_logger(), "Warte auf die Gazebo-Pose des Go2.");
    }
  }

private:
  void poseCallback(const gz::msgs::Pose_V &msg)
  {
    for (int i = 0; i < msg.pose_size(); ++i)
    {
      const auto &pose = msg.pose(i);

      if (pose.name() != "go2")
      {
        continue;
      }

      geometry_msgs::msg::TransformStamped tf;
      const auto &stamp = msg.header().stamp();
      tf.header.stamp.sec = static_cast<int32_t>(stamp.sec());
      tf.header.stamp.nanosec = static_cast<uint32_t>(stamp.nsec());
      tf.header.frame_id = "odom";
      tf.child_frame_id = "trunk";

      tf.transform.translation.x = pose.position().x();
      tf.transform.translation.y = pose.position().y();
      tf.transform.translation.z = pose.position().z();

      tf.transform.rotation.x = pose.orientation().x();
      tf.transform.rotation.y = pose.orientation().y();
      tf.transform.rotation.z = pose.orientation().z();
      tf.transform.rotation.w = pose.orientation().w();

      broadcaster_->sendTransform(tf);
      return;
    }
  }

  gz::transport::Node gz_node_;
  std::unique_ptr<tf2_ros::TransformBroadcaster> broadcaster_;
};

int main(int argc, char **argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<SlamPoseBridge>());
  rclcpp::shutdown();
  return 0;
}
