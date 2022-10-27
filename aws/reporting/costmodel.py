# cost models for different dev environments
from datetime import datetime
from math import ceil

from pricing import get_price_for_instance

models_ec2 = {
    'ocp-dev-3': [
        (1, 't2.large'),
        (1, 'm5.large'),
        (1, 'm5.2xlarge'),
        (3, 'm5.xlarge'),
        (3, 'm5.large')
    ],
    'ocp-dev-4': [
        (1, 't2.medium'),
        (3, 'm5.xlarge'),
        (3, 'm5.xlarge')
    ],
    'ocs-dev-4': [
        (1, 't2.medium'),
        (3, 'm5.2xlarge'),
        (3, 'm5.2xlarge')
    ]
}

considered_regions = [
    'us-east-1',
    'us-east-2',
    'us-west-1',
    'us-west-2',
    'eu-central-1',
    'eu-west-1',
    # 'eu-west-2'
]

def get_avg_cost_for_ec2_model(model):
    model_cost = []
    for count, instance_type in models_ec2[model]:
        avg_cost = 0.0
        for r in considered_regions:
            avg_cost += get_price_for_instance(instance_type, r) * 24.0 * 30
        avg_cost /= len(considered_regions)
        avg_cost *= count
        avg_cost = ceil(avg_cost)
        model_cost.append((count, instance_type, avg_cost))
    return model_cost

def to_rich_text(model):
    text = ""
    for m in model:
        text += """
{} x {} = ${}
""".format(m[0], m[1], m[2])
    return text

def get_total_for_model(model):
    total = 0.0
    for m in model:
        total += m[2]
    return total

if __name__ == "__main__":
    summary = """
Updated On: {}

Following is a summary of costs for different development environmets used by Migration devs. 

The estimation is based on latest costs of EC2 instances averaged over all regions we are in.

The instance sizes are assumed based on defaults in mig-agnosticd.

OCP 3 -> 4 Environment

OCP 3
{}
Total : ${}

OCP 4
{}
Total : ${}

OCS 3 -> 4 Environments

OCS 3
{}
Total : ${}

OCS 4
{}
Total : ${}

"""
    # document_id = os.environ['DOC_ID']
    now = (datetime.utcnow()).strftime("%a, %b %d, %y")
    ocp3_model = get_avg_cost_for_ec2_model('ocp-dev-3')
    ocp4_model = get_avg_cost_for_ec2_model('ocp-dev-4')
    ocs3_model = get_avg_cost_for_ec2_model('ocp-dev-3')
    ocs4_model = get_avg_cost_for_ec2_model('ocs-dev-4')
    # googleDocEditor = GoogleDocEditor(document_id)

    summary = summary.format(
        now, 
        to_rich_text(ocp3_model), get_total_for_model(ocp3_model), 
        to_rich_text(ocp4_model), get_total_for_model(ocp4_model),
        to_rich_text(ocs3_model), get_total_for_model(ocs3_model),
        to_rich_text(ocs4_model), get_total_for_model(ocs4_model)
        )
    
    print(summary)

    
