import argparse
import numpy as np

def create_hmac_salts(dxcallsign: str, mycallsign: str, num_tokens: int = 10000):
    """
    Creates a file with tokens for hmac signing

    Args:
        dxcallsign:
        mycallsign:
        int:

    Returns:
        bool
    """
    try:
        token_array = []
        for _ in range(num_tokens):
            token_array.append(np.random.bytes(4).hex())

        # Create and write random strings to a file
        with open(f"freedata_hmac_STATION_{mycallsign}_REMOTE_{dxcallsign}.txt", "w") as file:
            for _ in range(len(token_array)):
                file.write(token_array[_] + '\n')



    except Exception:
        print("error creating hmac file")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='FreeDATA token generator')

    parser.add_argument('--dxcallsign', dest="dxcallsign", default='AA0AA', help="Select the destination callsign", type=str)
    parser.add_argument('--mycallsign', dest="mycallsign", default='AA0AA', help="Select the own callsign", type=str)
    parser.add_argument('--tokens', dest="tokens", default='10000', help="Amount of tokens to create", type=int)

    args = parser.parse_args()

    create_hmac_salts(args.dxcallsign, args.mycallsign, int(args.tokens))

