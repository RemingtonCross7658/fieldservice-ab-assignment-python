import unittest

from fieldservice_experiment import assign_variant


class AssignmentTest(unittest.TestCase):
    def test_assignment_is_stable_for_a_technician(self):
        first = assign_variant("tech-17")
        self.assertIn(first, {"control", "follow-up"})
        self.assertEqual(first, assign_variant("tech-17"))
        self.assertNotEqual(first, assign_variant("tech-19"))


if __name__ == "__main__":
    unittest.main()
