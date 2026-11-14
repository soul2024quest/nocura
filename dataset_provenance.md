Where This Data Comes From-

This dataset (bass2_pmma_flammability_data-v3.csv) contains 51 data points taken from NASA's Burning and Suppression of Solids - II (BASS-II) experiment, which ran inside the Microgravity Science Glovebox on the International Space Station. The official data and reports are hosted on NASA's Physical Sciences Informatics (PSI) portal under investigation ID PSI-25 (https://psi.nasa.gov/physci/repo/data/investigations/PSI-25) and published in NASA Technical Reports NTRS 20160000593 and NASA/TM-20210011385.

What Was Tested

In these tests, astronauts and ground researchers burned small cylindrical rods made of cast PMMA (clear acrylic plastic) with a fixed diameter of 6.35 mm (1/4 inch) inside a low-speed microgravity wind tunnel. The goal was to find the exact oxygen levels and airflow speeds where a flame keeps burning versus where it dies out.

What Each Column Means

ambient_o2_percent: The percentage of oxygen in the test chamber (ranges from 13.5% to 21.9%).

flow_velocity_cms: The speed of the air blowing past the plastic rod in centimeters per second (ranges from 0.106 to 16.298 cm/s).

fuel_thickness_mm: The thickness of the plastic rod. It is 6.35 mm for every single row, so the model ignores it during training.

stretch_rate_s_inv: A physics value calculated directly from the airflow speed and rod size. Because it is just a math formula based on airflow speed, the model ignores it so it doesn't double-count the same information.

flame_hazard_state: The final test result. 1 means the flame stayed lit and kept burning. 0 means the flame went out on its own—either because the airflow was too slow to feed it oxygen, or too fast and blew it out.

How the Numbers Were Collected

The 51 rows were read and digitized directly from the official flammability boundary charts published in NASA's BASS-II research papers for 6.35 mm PMMA rods.
