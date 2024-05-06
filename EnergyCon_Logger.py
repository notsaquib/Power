
#Energy Consumption + Loguru
#Use Elasticsearch and kibana to visualise log files
# This code currently accepts Product name. Opens the product yaml, 
#fetches the machines required to produce the product. With this machine list, 
#it compares it to the different factory machine lists. Whichever factory has all the machines required, that factory is chosen. 
#Then the machine yaml is opened and elec info about the machines are fetched. Energy consumption is calculated based on time units and power.


#Next update is to give the prodcut. The factory templates are searched for the product.If found, the machines in the factory are fetched. Machine yaml conetnts like, 
#power ID are fetched. From product yaml, time units and machine sequence are fetched
#And using this Energy consumption is calculated.
import os
import yaml
import json
from loguru import logger


def load_yaml_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            data = yaml.safe_load(file)
        return data
    else:
        logger.error(f"Product does not exist: {file_path}")
        return None

def load_config(config_file_path="config.json"):
    with open(config_file_path, "r") as config_file:
        config = json.load(config_file)
    return config

def find_matching_factory(product_machines, factories, product_list):
    unmatched_machines = []
    for product_name in product_list:
        logger.info(f"Checking Product")  
        for factory_size, factory_machines in factories.items():
            unmatched = [machine for machine in product_machines if machine not in factory_machines]
            if not unmatched:  # If all machines are matched
                return factory_size
            unmatched_machines = unmatched
            logger.info(f"Add {unmatched_machines} to the factory {factory_size}")
        return None



def calculate_power_consumed(product_name,config):
    root_folder = config.get("root_directory", "")
    # Loads product information
    product_file_path = os.path.join(root_folder, "products", f"{product_name.lower()}.yaml")
    product_data = load_yaml_file(product_file_path)
    product_machines = []

    # Extract machine names from product's processing steps
    for sub_product in product_data.get("sub_products", []):
        for processing_step in sub_product.get("processing_steps", []):
            machine_name = processing_step.get("machine_name")
            product_machines.append(machine_name)
    logger.info(f"Machine sequence for {product_name}: {'--> '.join(product_machines)}")
    #print("Product Machines:", product_machines)

    
    

    # Loads factory information
    Templates = config.get("templates", "")
    factories_file_path = os.path.join(root_folder, "factories/Templates")
    factories = {}
    for factory_size in Templates:  
        factory_file_path = os.path.join(factories_file_path, f"{factory_size}.yaml")
        factory_data = load_yaml_file(factory_file_path)
        factory_floors = factory_data.get("factory_floor", {})  # Fetch as dictionary instead of list
        #print(f"Factory floors in {factory_size}: {factory_floors}")  # Debugging statement


        # Iterate through factory floors and their sections
        for factory_floor_name, floor_data in factory_floors.items():
            sections = floor_data.get("sections", [])
            machines_list = []
            for section in sections:
                section_name = section.get("name")
                machines = section.get("machines", [])
                machines_list.extend(machines)
                #print(f"Machines in section {section_name}: {machines}")  # Debugging statement

            product_list = floor_data.get("products", [])
            #print(f"Products in factory floor {factory_floor_name}:{product_list}")  # Debugging statement

            if product_name in product_list:
                if set(product_machines).issubset(machines_list):
                    logger.info(f"Product {product_name} found in factory floor {factory_floor_name} of factory {factory_size}")
                    calculate_power_consumption_for_factory(factory_size, product_data, root_folder,floor_data,factory_floor_name)
                    return factory_size




        factories[factory_size] = machines_list
    #print(f"Machines: {factories}")

    
    # Find the matching factory
    # matched_factory = find_matching_factory(product_machines, factories, product_list)
    # return matched_factory
    #if matched_factory:
        #logger.info(f"The product can be produced in the {matched_factory} factory.")
        #calculate_power_consumption_for_factory(matched_factory, product_data, root_folder)
    #else:
        #logger.warning("No matching factory found for the given product.")



def calculate_power_consumption_for_factory(factory_size, product_data, root_folder,floor_data,factory_floor_name):
    total_power_consumed = 0
    total_time_units = 0
    section_energy_consumption = {}
    sections = floor_data.get("sections", [])

    # Iterate through sections and calculate power consumption
    for section in sections:
            section_name = section.get("name", "")
            section_energy_consumption[section_name] = 0


            # Iterate through sub-products and calculate power consumption for the section
            for sub_product in product_data.get("sub_products", []):
                for processing_step in sub_product.get("processing_steps", []):
                    machine_name = processing_step.get("machine_name")

                    # Check if the machine is in the current section
                    if machine_name in section.get("machines", []):
                        time_units = processing_step.get("time_units", 0)
                        total_time_units += time_units

                        # Find the machine information
                        machine_file_path = os.path.join(root_folder, "machines", f"{machine_name}.yaml")
                        machine_data = load_yaml_file(machine_file_path)

                        # Generate unique machine ID
                        machine_id = machine_data.get("id")
                        logger.info(f"Machine ID: {machine_id}")

                        electric_spec = machine_data.get("electric_spec", {})
                        peak_power = electric_spec.get("peak_power", 0)
                        idle_power = electric_spec.get("idle_power", 0)
                        duty_cycle = electric_spec.get("duty_cycle", 1.0)

                        # Calculate power consumption based on time spent and machine specifications
                        operational_time_units = time_units * duty_cycle
                        idle_time_units = round(time_units * (1 - duty_cycle),2)

                        logger.info(f"Peak time for {machine_id}: {operational_time_units}")
                        logger.info(f"Idle time for {machine_id}: {idle_time_units}")
                        logger.info(f"Total time units for {machine_id}: {operational_time_units + idle_time_units}")

                        power_consumed_operational = operational_time_units * peak_power
                        power_consumed_idle = idle_time_units * idle_power

                        machine_power_consumed = round (power_consumed_operational + power_consumed_idle,2)

                        # Consider green energy based on the tag
                        green_energy_tag = machine_data.get("renewable_capable", "no").lower()
                        if green_energy_tag == "yes":
                            machine_power_consumed *= 0.5
                        elif green_energy_tag == "partial":
                            machine_power_consumed *= 0.7

                        section_energy_consumption[section_name] += round (machine_power_consumed,1)

                        #To print Energy consumption of each machine
                        #print(f"Total Energy consumed for {machine_name} in {section_name}: {machine_power_consumed} kW")

                        total_power_consumed += round (machine_power_consumed,1)
    for section_name, energy_consumption in section_energy_consumption.items():
        logger.info(f"Total Energy consumed in {section_name} of {factory_floor_name}: {energy_consumption} kWh")
    
    
        



    logger.info(f"Total Energy consumed in the {factory_size} factory to produce the product: {total_power_consumed} kWh")
    logger.info(f"Total time units to produce the product: {total_time_units}")


if __name__ == "__main__":

    logger.add("power_consumption.log", rotation="500 MB", level="INFO")

    config = load_config()
    product_name = input("Enter the product name: ")
    calculate_power_consumed(product_name.lower(),config)