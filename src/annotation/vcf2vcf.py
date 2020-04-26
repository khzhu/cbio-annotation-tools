import os
import stat
import argparse
from string import Template

def get_options():

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", type=str, required=True,
                        help="Path to input file, a VCF or VCF-like format")
    parser.add_argument("-o", "--output", type=str, required=True,
                        help="Path to output file, a standardized VCF format")
    return parser.parse_args()

def main():
    args = get_options()
    print(args)
    # convert to a standardized VCF from a given VCF
    s = Template('perl /gpfs/data/molecpathlab/bin/vcf2maf-1.6.17/vcf2vcf.pl\
                    --input-vcf $input_vcf\
                    --output-vcf $output_vcf\)

    input_dir = args.input
    ouput_dir = args.output
    for subdir, dirs, files in os.walk(vep_dir):
        for file in files:
            if file.endswith("vep.vcf"): continue
            if file.endswith("vcf"):
                vcf_file = os.path.join(ouput_dir, "{}".format(file)))
                if os.path.exists(vcf_file): continue

                d = dict(
                         input_vcf = os.path.join(input_dir, file),
                         out_vcf = vcf_file)
                cmd = s.substitute(d)
                print (cmd)
                script_dir = os.path.join(ouput_dir, "vcf_script")
                if not os.path.exists(script_dir):
                    try:
                        os.mkdir(script_dir,0755)
                    except OSError as e:
                        print ("Error:Script directory exists")
                out_file = os.path.join(script_dir,"{}".format(file.replace('vcf', 'sh')))
                with open(out_file, 'w') as of:
                    of.write("#!/bin/bash\n")
                    of.write("#SBATCH -t 2:0:0\n")
                    of.write("#SBATCH --mem=8G\n")
                    of.write("#SBATCH -J NGS-VEP\n")
                    of.write("#SBATCH -p cpu_short\n")
                    of.write("#SBATCH -c 4\n")
                    of.write("#SBATCH -N 1\n")
                    of.write("#SBATCH -o %x-%j.out\n")
                    of.write("module load perl/5.28.0\n")
                    of.write("module load samtools/1.9\n")
                    of.write(cmd)
                print (out_file)
                os.chmod(out_file, stat.S_IRWXU)
if __name__ == "__main__":
    main()
