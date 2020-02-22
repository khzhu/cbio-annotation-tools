import os
import stat
import argparse
from string import Template
import subprocess

def get_options():

    parser = argparse.ArgumentParser()
    parser.add_argument("--species", type=str, required=False,
                        help="Ensembl-friendly name of species (e.g. mus_musculus for mouse)", default="homo_sapiens")
    parser.add_argument("--vep_data", type=str, required=False,
                        help="VEP's base cache/plugin directory", default='/gpfs/data/abl/home/zhuh05/.vep')
    parser.add_argument("--vep_path", type=str, required=False,
                        help="Folder containing the vep script", default="/gpfs/share/apps/vep/raw/ensembl-vep/vep")
    parser.add_argument("-f", "--fasta", type=str, required=False,
                        help="Reference FASTA file including path",
                        default="/gpfs/data/igorlab/ref/hg19/genome.fa")
    parser.add_argument("-i", "--input", type=str, required=True,
                        help="Path to input file in VCF format")
    parser.add_argument("-o", "--output", type=str, required=True,
                        help="Path to output MAF file")
    parser.add_argument("--ncbi_build", type=str,
                        help="NCBI genome build name e.g. GRCh37", default="GRCh37")
    parser.add_argument("--vcf_TUMOR", type=str, required=False,
                        help="Tumor sample ID used in VCF's genotype columns", default="TUMOR")
    parser.add_argument("--vcf_NORMAL", type=str, required=False,
                        help="Matched normal ID used in VCF's genotype columns", default="NORMAL")
    parser.add_argument("--maf_center", type=str, required=False,
                        help="Variant calling center to report in MAF", default="MuTect2")
    parser.add_argument("--filter_vcf", type=str, required=False,
                        help="A VCF for FILTER common_variant.",
                        default="/gpfs/home/zhuh05/ablhome/ExAC/ExAC.r0.3.sites.vep.hg19.vcf.gz")
    parser.add_argument("--separator", type=str, required=False,
                        help="Delimiter to separate sample ID", default="_")
    parser.add_argument("-t", "--debug", action="store_true",
                        help="Debug mode for testing")
    return parser.parse_args()

def get_sampleIDs_from_filename(file_name, separator, pos):
    try:
        sample_id = file_name.strip().split(separator)[pos]
        return sample_id, sample_id.replace("T","N")
    except:
        return None, None

def get_sampleIDs_from_vcf_header(vcf_file):
    try:
        p = subprocess.Popen(['grep', '#CHROM', vcf_file], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        parts = p.communicate()[0].split("\n")
        parts = parts[0].split("\t")
        return (parts[-2],parts[-1])
    except:
        return None, None

def main():
    args = get_options()
    print(args)
    #run vcf2maf using the retain-info option to retain gnomAD AF_POPMAX allele frequencies
    s = Template('perl /gpfs/home/zhuh05/molecpathlab/bin/vcf2maf-1.6.17/vcf2maf.pl\
                    --species $species\
                    --ncbi-build $ncbi_build\
                    --input-vcf $input_vcf\
                    --output-maf $out_maf\
                    --maf-center $maf_center\
                    --tumor-id $tumor_id\
                    --normal-id $normal_id\
                    --vcf-tumor-id $vcf_TUMOR\
                    --vcf-normal-id $vcf_NORMAL\
                    --vep-path $vep_path\
                    --vep-data $vep_data\
                    --ref-fasta $fasta\
                    --filter-vcf $filter_vcf\
                    --buffer-size 265\
                    --max-filter-ac 10\
                    --retain-info gnomAD_AF_POPMAX,gnomAD_AF_AFR,gnomAD_AF_AMR,gnomAD_AF_ASJ,gnomAD_AF_EAS,gnomAD_AF_FIN,gnomAD_AF_NFE,gnomAD_AF_OTH,gnomAD_AF_SAS\
                    --min-hom-vaf 0.7')

    vep_dir = args.input
    ouput_dir = args.output
    for subdir, dirs, files in os.walk(vep_dir):
        for file in files:
            if file.endswith("vep.vcf"): continue
            if file.endswith("vcf"):
                maf_file = os.path.join(ouput_dir, "{}".format(file.replace('vcf','maf')))
                if os.path.exists(maf_file): continue
                vep_file = os.path.join(vep_dir, file)
                print (vep_file)
                sample_id, normal_id = get_sampleIDs_from_filename(file, args.separator, 5)
                print ("sample ID: {}".format(sample_id))
                print ("matched normal ID: {}".format(normal_id))

                d = dict(
                         species=args.species,
                         ncbi_build=args.ncbi_build,
                         input_vcf = os.path.join(vep_dir, file),
                         out_maf = maf_file,
                         maf_center = args.maf_center,
                         vep_data=args.vep_data,
                         vep_path=args.vep_path,
                         fasta=args.fasta,
                         filter_vcf = args.filter_vcf,
                         vcf_TUMOR= args.vcf_TUMOR,
                         vcf_NORMAL=args.vcf_NORMAL,
                         tumor_id=sample_id,
                         normal_id=normal_id)
                cmd = s.substitute(d)
                print (cmd)
                script_dir = os.path.join(ouput_dir, "maf_script")
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
                    of.write("#SBATCH -J NGS629_VEP\n")
                    of.write("#SBATCH -p cpu_short\n")
                    of.write("#SBATCH -c 4\n")
                    of.write("#SBATCH -N 1\n")
                    of.write("#SBATCH -o %x-%j.out\n")
                    of.write("module load perl/5.28.0\n")
                    of.write("module load vep/96\n")
                    of.write("module load samtools/1.9\n")
                    of.write(cmd)
                print (out_file)
                os.chmod(out_file, stat.S_IRWXU)
if __name__ == "__main__":
    main()
