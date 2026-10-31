from action_msgs.srv import CancelGoal


def cancel_navigation(controller):
    client = controller.create_client(
        CancelGoal,
        "/navigate_to_pose/_action/cancel_goal"
    )

    if not client.wait_for_service(timeout_sec=1.0):
        controller.get_logger().warning(
            "Nav2-Abbruchdienst nicht erreichbar"
        )
        return False

    request = CancelGoal.Request()

    # Leere Goal-ID und Zeitstempel 0:
    # Alle aktiven Navigationsziele abbrechen.
    future = client.call_async(request)

    def on_cancel_done(result_future):
        try:
            response = result_future.result()
            controller.get_logger().info(
                f"Nav2-Abbruch: Rückgabecode {response.return_code}"
            )
        except Exception as error:
            controller.get_logger().error(
                f"Nav2-Abbruch fehlgeschlagen: {error}"
            )

    future.add_done_callback(on_cancel_done)
    return True
