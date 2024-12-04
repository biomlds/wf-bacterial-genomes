"""Collect results into wf.Sample."""

import json
import os

import numpy as np
import pandas as pd
import vcf
import workflow_glue.results_schema as wf
from .parsers import parse_prokka_gff  # noqa: ABS101
from .process_resfinder_iso import get_acquired_data, get_point_data  # noqa: ABS101
from .util import get_named_logger, wf_parser  # noqa: ABS101


# fastcat is there temporarily until CW-3217
def gather_sample_files(alias, data_dir):
    """Collect files required for the model and make sure they exist."""
    files = {
        "depth": os.path.join(data_dir, f"{alias}.total.regions.bed.gz"),
        "variants": os.path.join(data_dir, f"{alias}.medaka.vcf.gz"),
        "prokka": os.path.join(data_dir, f"{alias}.prokka.gff"),
        "mlst": os.path.join(data_dir, f"{alias}.mlst.json"),
        "amr": os.path.join(
            data_dir, f"{alias}_resfinder_results/{alias}_resfinder.json"
        ),
        "fastcat": os.path.join(data_dir, "fastcat_stats/per-read-stats.tsv.gz"),
        "len_hist": os.path.join(data_dir, "fastcat_stats/length.hist"),
        "qual_hist": os.path.join(data_dir, "fastcat_stats/quality.hist"),
        "flye": os.path.join(data_dir, f"{alias}_flye_stats.tsv"),
        "serotype": os.path.join(data_dir, f"{alias}.serotype_results.json"),
    }

    # Return none if file does not exist
    files = {
        section: (file if os.path.exists(file) else None)
        for section, file in files.items()
    }

    return files


def fastcat_stats(len_hist, qual_hist):
    """Collect fastcat stats."""
    # hists can be empty in the case of fastcat filtering all reads
    qual_df = pd.read_csv(qual_hist, sep="\t", names=["lower", "upper", "count"])
    mean_qual = 0
    if not qual_df.empty:
        mean_qual = np.average(
            qual_df["upper"] - qual_df["lower"], weights=qual_df["count"]
        )

    n_seqs = 0
    n_bases = 0
    min_length = 0
    max_length = 0
    len_df = pd.read_csv(len_hist, sep="\t", names=["lower", "upper", "count"])
    if not len_df.empty:
        n_seqs = len_df["count"].sum()
        n_bases = (len_df["lower"] * len_df["count"]).sum()
        min_length = len_df["lower"].min()
        max_length = len_df["lower"].max()

    result = wf.FastqStats(
        n_seqs=n_seqs,
        n_bases=n_bases,
        min_length=min_length,
        max_length=max_length,
        mean_quality=mean_qual,
    )

    return result


def parse_mlst(mlst_file):
    """Extract schema and sequence type from MLST json."""
    with open(mlst_file, "r") as f:
        mlst = json.loads(f.read())[0]

    alleles = []
    if mlst["alleles"]:
        for schema_id, allele in mlst["alleles"].items():
            alleles.append(
                wf.SequenceTypeSchema(
                    schema_identifier=schema_id, allele_variant=allele
                )
            )
    result = wf.MLST(
        detected_species=mlst["scheme"],
        sequence_type=mlst["sequence_type"],
        typing_schema=alleles,
    )

    return result


def parse_serotyping(serotype_file, return_df=False):
    """Extract serotyping information from SISTR."""
    with open(serotype_file) as f:
        sistr_profile = json.load(f)[0]
        h1 = str(sistr_profile.get("h1", "-"))
        h2 = str(sistr_profile.get("h2", "-"))
        o_antigen = str(sistr_profile.get("o_antigen", "-"))
        serovar = sistr_profile.get("serovar", "-")
        qc_status = sistr_profile.get("qc_status", "-")
        predicted_antigenic_profile = f"{o_antigen}:{h1}:{h2}"

        serotype = wf.Serotype(
            predicted_serotype=serovar,
            predicted_antigenic_profile=predicted_antigenic_profile,
            o_antigen_predicition=o_antigen,
            h1_antigen_prediction=h1,
            h2_antigen_prediction=h2,
            qc_status=qc_status,
        )

        if return_df is True:
            sero_df = pd.DataFrame(
                {
                    "Predicted serotype": [serovar],
                    "Predicted antigenic profile": [predicted_antigenic_profile],
                    "O antigen prediction": [o_antigen],
                    "H1 antigen prediction(fliC)": [h1],
                    "H2 antigen prediction(fljB)": [h2],
                    "QC status": [qc_status],
                }
            )
            return sero_df

        return serotype


def contig_stats(total_coverage):
    """Get coverage details for assembly."""
    contigs = []
    depth_df = pd.read_csv(
        total_coverage, sep="\t", names=["ref", "start", "end", "depth"]
    )
    for contig, df in depth_df.groupby("ref"):
        coverage = wf.Coverage(
            counts=df["depth"].sum(),
            median=df["depth"].median(),
            mean=df["depth"].mean(),
            minimum=df["depth"].min(),
            maximum=df["depth"].max(),
        )
        contigs.append(
            wf.Contig(name=contig, length=df["end"].max(), coverage=coverage)
        )
    return contigs


def variant_stats(vcf_file):
    """Extract basic variant information from vcf file."""
    vcf_reader = vcf.Reader(filename=vcf_file)
    variants = []
    for record in vcf_reader:
        for alt in record.ALT:
            variants.append(
                wf.Variant(
                    contig=record.CHROM,
                    pos=record.POS,
                    ref=record.REF,
                    alt=str(alt),
                    depth=record.INFO["DP"],
                )
            )
    return variants


def assembly_stats(params_data, files):
    """Gather assembly statistics for sample."""
    contigs = []
    if files["depth"]:
        contigs = contig_stats(files["depth"])

    variants = []
    if files["variants"]:
        variants = variant_stats(files["variants"])

    annotation = []
    if files["prokka"]:
        annotation = parse_prokka_gff(files["prokka"])
        annotation = annotation.rename(columns={"EC number": "ec_number"})
        annotation = annotation.to_dict("records")

    assembly = wf.Assembly(
        reference=params_data["reference"],
        annotations=annotation,
        contig=contigs,
        variants=variants,
    )

    return assembly


def antimicrobial_stats(resfinder_json):
    """Gather amr results from resfinder."""
    antimicrobial_details = []
    with open(resfinder_json) as f:
        resfinder_data = json.loads(f.read())
    antimicrobial_details.extend(get_acquired_data(resfinder_data).values())
    point_data = get_point_data(resfinder_data)
    for gene in point_data.values():
        antimicrobial_details.extend(gene)
    results = wf.AntimicrobialResistance(detected_variants=antimicrobial_details)
    return results


def main(args):
    """Run the entry point."""
    logger = get_named_logger("collect_results")
    with open(args.params, "r") as f:
        params_data = json.loads(f.read())

    alias = args.alias

    files = gather_sample_files(args.alias, args.data_dir)

    assembly = assembly_stats(params_data, files)

    sequence_type = {}
    if files["mlst"]:
        sequence_type = parse_mlst(files["mlst"])

    antimicrobial_details = {}
    if files["amr"]:
        antimicrobial_details = antimicrobial_stats(files["amr"])

    serotype = {}
    if files["serotype"]:
        serotype = parse_serotyping(files["serotype"])

    fastcat = {}
    if files["len_hist"] and files["qual_hist"]:
        fastcat = fastcat_stats(files["len_hist"], files["qual_hist"])

    results = wf.ResultsContents(
        antimicrobial_resistance=antimicrobial_details,
        assembly=assembly,
        sequence_typing=sequence_type,
        serotyping=serotype,
        fastq=fastcat,
    )

    sample = wf.Sample(
        alias=alias, sample_type=args.type, results=results, barcode=args.barcode
    )

    with open(args.output, "w") as f:
        f.write(json.dumps(sample.dict(), indent=4))

    logger.info(f"results collected and written to {args.output}.")


def argparser():
    """Argument parser for entrypoint."""
    parser = wf_parser("collect_results")
    parser.add_argument("--output", help="Report output filename")
    parser.add_argument("--params", required=True)
    parser.add_argument("--alias", required=True)
    parser.add_argument("--barcode", required=True)
    parser.add_argument("--data_dir", required=True, help="Analysis results directory")
    parser.add_argument("--type")
    return parser
